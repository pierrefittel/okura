const { createApp } = Vue

createApp({
    data() {
        return {
            currentTab: 'analyze',
            sourceText: '', readerMode: false, isLoading: false, analyzedSentences: [],
            selectedToken: null, currentContextSentence: [], highlightLevel: 0,
            
            lists: [], selectedListId: null, activeList: null, showCreateListModal: false, newListTitle: '',
            
            dueCards: [], currentCard: null, isFlipped: false, trainListId: null,
            stats: { total_cards: 0, cards_learned: 0, due_today: 0, heatmap: {} }
        }
    },
    computed: {
        heatmapDays() {
            const days = [];
            for (let i = 29; i >= 0; i--) {
                const d = new Date(); d.setDate(d.getDate() - i);
                const dateStr = d.toISOString().split('T')[0];
                days.push({ date: dateStr, count: this.stats.heatmap[dateStr] || 0 });
            }
            return days;
        }
    },
    mounted() { this.fetchLists(); this.fetchStats(); },
    watch: {
        currentTab(newTab) {
            if (newTab === 'train') this.startSession();
            if (newTab === 'dashboard') this.fetchStats();
        }
    },
    methods: {
        // --- READER ---
        async analyzeText() {
            if (!this.sourceText) return;
            this.isLoading = true;
            try {
                const res = await fetch('/lists/analyze', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ text: this.sourceText }) });
                const data = await res.json();
                this.analyzedSentences = data.sentences;
                this.readerMode = true; this.selectedToken = null;
            } catch (e) { alert("Erreur"); } finally { this.isLoading = false; }
        },
        selectToken(token, sentence) { this.selectedToken = token; this.currentContextSentence = sentence; },
        extractContextString(tokens) { return tokens ? tokens.map(t => t.text).join('') : ""; },
        getHighlightClass(token) {
            if (this.highlightLevel === 1 && (!token.jlpt || token.jlpt === 1)) return 'highlight-hard';
            return '';
        },
        async saveCurrentToken() {
            if (!this.selectedToken || !this.selectedListId) return;
            const payload = [{
                terme: this.selectedToken.lemma, lecture: this.selectedToken.reading, pos: this.selectedToken.pos,
                ent_seq: this.selectedToken.ent_seq, definitions: this.selectedToken.definitions,
                context: this.extractContextString(this.currentContextSentence)
            }];
            try {
                const res = await fetch(`/lists/${this.selectedListId}/cards/bulk`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
                // Modification ici : Plus d'alerte, sauvegarde silencieuse
                if (res.ok) {
                    console.log("Mot sauvegardé"); 
                }
            } catch (e) { alert("Erreur"); }
        },

        // --- TRAIN ---
        async startSession() {
            this.currentCard = null; this.isFlipped = false;
            let url = '/lists/training/due';
            if (this.trainListId) url += `?list_id=${this.trainListId}`;
            try {
                const res = await fetch(url);
                this.dueCards = await res.json();
                this.nextCard();
            } catch (e) { console.error(e); }
        },
        nextCard() { this.currentCard = this.dueCards.length ? this.dueCards[0] : null; this.isFlipped = false; },
        flipCard() { this.isFlipped = true; },
        async submitReview(q) {
            await fetch(`/lists/cards/${this.currentCard.id}/review`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({quality: q}) });
            this.dueCards.shift();
            this.nextCard();
        },

        // --- LISTS & CRUD ---
        async fetchLists() {
            const res = await fetch('/lists/');
            this.lists = await res.json();
            if (!this.selectedListId && this.lists.length) this.selectedListId = this.lists[this.lists.length-1].id;
        },
        async openList(list) {
            const res = await fetch(`/lists/${list.id}`);
            this.activeList = await res.json();
        },
        async createNewList() {
            if (!this.newListTitle) return;
            await fetch('/lists/', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ title: this.newListTitle }) });
            this.newListTitle = ''; this.showCreateListModal = false; await this.fetchLists();
        },
        async deleteCard(id) {
            if(!confirm("Supprimer ?")) return;
            await fetch(`/lists/cards/${id}`, {method: 'DELETE'});
            if (this.activeList) this.activeList.cards = this.activeList.cards.filter(c => c.id !== id);
        },
        
        // --- DASH ---
        async fetchStats() {
            const res = await fetch('/lists/dashboard/stats');
            this.stats = await res.json();
        },
        getHeatClass(c) {
            if (!c) return '';
            if (c <= 5) return 'heat-1'; if (c <= 10) return 'heat-2';
            if (c <= 20) return 'heat-3'; return 'heat-4';
        },

        // --- DATA ---
        downloadCsv() {
            window.location.href = "/lists/data/export";
        },
        async uploadCsv(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const res = await fetch('/lists/data/import', {
                    method: 'POST',
                    body: formData
                });
                if (res.ok) {
                    const data = await res.json();
                    alert(`Import réussi : ${data.details.cards_created} cartes créées.`);
                    this.fetchStats(); // Met à jour le dashboard
                    this.fetchLists(); // Met à jour les listes
                } else {
                    alert("Erreur lors de l'import");
                }
            } catch (e) {
                alert("Erreur réseau");
            }
        },
    }
}).mount('#app')