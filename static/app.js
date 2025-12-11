const { createApp } = Vue

createApp({
    data() {
        return {
            currentTab: 'analyze',
            
            // ANALYSE
            sourceText: '',
            isLoading: false,
            candidates: [],
            
            // LISTES
            lists: [],
            selectedListId: null,
            activeList: null,
            
            // TRAINING
            dueCards: [],
            currentCard: null,
            isFlipped: false,
            
            // DASHBOARD
            stats: { total_cards: 0, cards_learned: 0, due_today: 0, heatmap: {} },
            
            // MODAL
            showCreateListModal: false,
            newListTitle: ''
        }
    },
    computed: {
        selectedCandidates() {
            return this.candidates ? this.candidates.filter(c => c.selected) : [];
        },
        heatmapDays() {
            // Génère les 30 derniers jours pour l'affichage
            const days = [];
            for (let i = 29; i >= 0; i--) {
                const d = new Date();
                d.setDate(d.getDate() - i);
                const dateStr = d.toISOString().split('T')[0];
                days.push({
                    date: dateStr,
                    count: this.stats.heatmap[dateStr] || 0
                });
            }
            return days;
        }
    },
    mounted() {
        this.fetchLists();
        this.fetchStats(); // Charge les stats au démarrage
    },
    watch: {
        currentTab(newTab) {
            if (newTab === 'train') this.startSession();
            if (newTab === 'dashboard') this.fetchStats();
        }
    },
    methods: {
        // --- DASHBOARD ---
        async fetchStats() {
            try {
                const res = await fetch('/lists/dashboard/stats');
                this.stats = await res.json();
            } catch (e) { console.error("Erreur stats", e); }
        },
        getHeatClass(count) {
            if (count === 0) return '';
            if (count <= 5) return 'heat-1';
            if (count <= 10) return 'heat-2';
            if (count <= 20) return 'heat-3';
            return 'heat-4';
        },

        // --- TRAIN ---
        async startSession() {
            this.currentCard = null;
            this.isFlipped = false;
            try {
                const res = await fetch('/lists/training/due');
                this.dueCards = await res.json();
                this.nextCard();
            } catch (e) { console.error(e); }
        },
        nextCard() {
            if (this.dueCards.length > 0) {
                this.currentCard = this.dueCards[0];
                this.isFlipped = false;
            } else {
                this.currentCard = null;
                this.fetchStats(); // Refresh stats after session
            }
        },
        flipCard() { this.isFlipped = true; },
        async submitReview(quality) {
            if (!this.currentCard) return;
            try {
                await fetch(`/lists/cards/${this.currentCard.id}/review`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ quality: quality })
                });
                this.dueCards.shift();
                this.nextCard();
            } catch (e) { alert("Erreur save"); }
        },

        // --- LISTS & CRUD ---
        async fetchLists() {
            try {
                const res = await fetch('/lists/');
                this.lists = await res.json();
                if (this.lists.length > 0 && !this.selectedListId) {
                    this.selectedListId = this.lists[this.lists.length - 1].id;
                }
            } catch (e) { console.error(e); }
        },
        async openList(list) {
            try {
                const res = await fetch(`/lists/${list.id}`);
                this.activeList = await res.json();
            } catch (e) { alert("Erreur liste"); }
        },
        async deleteCard(cardId) {
            if (!confirm("Supprimer ?")) return;
            try {
                await fetch(`/lists/cards/${cardId}`, { method: 'DELETE' });
                this.activeList.cards = this.activeList.cards.filter(c => c.id !== cardId);
            } catch (e) { alert("Erreur"); }
        },
        async createNewList() {
            if (!this.newListTitle) return;
            try {
                const res = await fetch('/lists/', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ title: this.newListTitle })
                });
                if (res.ok) {
                    await this.fetchLists();
                    const n = await res.json();
                    this.selectedListId = n.id;
                    this.showCreateListModal = false;
                    this.newListTitle = '';
                }
            } catch (e) { alert("Erreur"); }
        },

        // --- ANALYZE ---
        async analyzeText() {
            if (!this.sourceText) return;
            this.isLoading = true;
            try {
                const res = await fetch('/lists/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ text: this.sourceText })
                });
                const data = await res.json();
                this.candidates = data.candidates.map(c => ({ ...c, selected: false }));
            } catch (e) { alert("Erreur analyse"); }
            finally { this.isLoading = false; }
        },
        async saveSelection() {
            if (!this.selectedListId) return;
            const payload = this.selectedCandidates.map(c => ({
                terme: c.terme, lecture: c.lecture, pos: c.pos, ent_seq: c.ent_seq, definitions: c.definitions,
                context: c.context // <-- ON ENVOIE LE CONTEXTE
            }));
            try {
                const res = await fetch(`/lists/${this.selectedListId}/cards/bulk`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    alert(`${payload.length} mots ajoutés !`);
                    this.candidates.forEach(c => c.selected = false);
                }
            } catch (e) { alert("Erreur import"); }
        },
        toggleWord(w) { w.selected = !w.selected; },
        formatDefs(d) { return (d && d.join) ? d.join('\n') : ''; }
    }
}).mount('#app')