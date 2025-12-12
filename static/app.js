const { createApp } = Vue

createApp({
    data() {
        return {
            currentTab: 'analyze',
            sourceText: '', readerMode: false, isLoading: false, analyzedSentences: [],
            selectedToken: null, currentContextSentence: [], highlightLevel: 0,
            lists: [], selectedListId: null, activeList: null, showCreateListModal: false, newListTitle: '',
            dueCards: [], currentCard: null, isFlipped: false, trainListId: null,
            stats: { total_cards: 0, cards_learned: 0, due_today: 0, heatmap: {} },
            importMsg: ''
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
        async uploadTextFile(event) {
            const file = event.target.files[0];
            if (!file) return;
            this.isLoading = true;
            const formData = new FormData();
            formData.append('file', file);
            try {
                const res = await fetch('/lists/analyze/file', { method: 'POST', body: formData });
                if (res.ok) {
                    const data = await res.json();
                    this.analyzedSentences = data.sentences;
                    this.readerMode = true; this.selectedToken = null;
                } else {
                    const err = await res.json();
                    alert("Erreur: " + err.detail);
                }
            } catch (e) { alert("Erreur upload"); }
            finally { this.isLoading = false; event.target.value = ''; }
        },
        async analyzeText() {
            if (!this.sourceText) return;
            this.isLoading = true;
            try {
                const res = await fetch('/lists/analyze', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ text: this.sourceText }) });
                const data = await res.json();
                this.analyzedSentences = data.sentences;
                this.readerMode = true; this.selectedToken = null;
            } catch (e) { alert("Erreur analyse"); } finally { this.isLoading = false; }
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
                if (res.ok) console.log("Sauvegardé");
            } catch (e) { alert("Erreur"); }
        },
        async saveAnalysis() {
             if (!this.sourceText) return;
             const name = prompt("Nom de la sauvegarde ?");
             if (!name) return;
             try {
                await fetch('/lists/', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ title: name, description: "Sauvegarde", source_text: this.sourceText })
                });
                alert("Sauvegardé !"); this.fetchLists();
             } catch(e) { alert("Erreur"); }
        },
        loadTextFromList(list) {
            if (list.source_text) {
                this.sourceText = list.source_text;
                this.currentTab = 'analyze';
                this.$nextTick(() => { this.analyzeText(); });
            }
        },

        // --- LISTS ---
        async createNewList() {
            if (!this.newListTitle) return;
            await fetch('/lists/', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ title: this.newListTitle }) });
            // FORCE LA FERMETURE ET LE RESET
            this.newListTitle = ''; 
            this.showCreateListModal = false; 
            await this.fetchLists();
        },
        // ... (Reste des fonctions inchangées: fetchLists, deleteCard, etc.) ...
        async fetchLists() {
            const res = await fetch('/lists/');
            this.lists = await res.json();
            if (!this.selectedListId && this.lists.length) this.selectedListId = this.lists[this.lists.length-1].id;
        },
        async openList(list) {
            const res = await fetch(`/lists/${list.id}`);
            this.activeList = await res.json();
        },
        async deleteCard(id) {
            try { await fetch(`/lists/cards/${id}`, {method: 'DELETE'}); if (this.activeList) this.activeList.cards = this.activeList.cards.filter(c => c.id !== id); } catch (e) {}
        },
        async deleteList(id) {
            if(!confirm("Supprimer ?")) return;
            await fetch(`/lists/${id}`, {method: 'DELETE'});
            this.lists = this.lists.filter(l => l.id !== id);
            if (this.activeList && this.activeList.id === id) this.activeList = null;
        },
        async startSession() {
            let url = '/lists/training/due'; if (this.trainListId) url += `?list_id=${this.trainListId}`;
            const res = await fetch(url); this.dueCards = await res.json(); this.nextCard();
        },
        nextCard() { this.currentCard = this.dueCards.length ? this.dueCards[0] : null; this.isFlipped = false; },
        flipCard() { this.isFlipped = true; },
        async submitReview(q) {
            await fetch(`/lists/cards/${this.currentCard.id}/review`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({quality: q}) });
            this.dueCards.shift(); this.nextCard();
        },
        async fetchStats() { const res = await fetch('/lists/dashboard/stats'); this.stats = await res.json(); },
        getHeatClass(c) { if (!c) return ''; if (c<=5) return 'heat-1'; return 'heat-4'; },
        downloadCsv() { window.location.href = "/lists/data/export"; },
        async uploadCsv(event) {
            const f = event.target.files[0]; if(!f) return; const d = new FormData(); d.append('file', f);
            const res = await fetch('/lists/data/import', {method:'POST', body:d});
            if(res.ok) { this.importMsg="Import OK"; setTimeout(()=>this.importMsg='',3000); this.fetchStats(); this.fetchLists(); }
        }
    }
}).mount('#app')