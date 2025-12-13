const { createApp } = Vue

createApp({
    data() {
        return {
            currentTab: 'analyze',
            currentLang: 'jp',
            sourceText: '', readerMode: false, isLoading: false, analyzedSentences: [],
            selectedToken: null, currentContextSentence: [], highlightLevel: 0,
            lists: [], selectedListId: null, activeList: null, 
            dueCards: [], currentCard: null, isFlipped: false, trainListId: null,
            stats: { total_cards: 0, cards_learned: 0, due_today: 0, heatmap: {} },
            
            // --- UI STATES ---
            toastMessage: '',
            showCreateListModal: false, newListTitle: '',
            
            // Analyse
            showSaveModal: false, newAnalysisTitle: '',
            showLoadModal: false, savedAnalyses: [],
            
            // Confirmation
            showConfirmModal: false, confirmMessage: '', confirmCallback: null
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
        // --- UTILITAIRES ---
        showToast(msg) {
            this.toastMessage = msg;
            setTimeout(() => this.toastMessage = '', 3000);
        },
        triggerConfirm(msg, callback) {
            this.confirmMessage = msg;
            this.confirmCallback = callback;
            this.showConfirmModal = true;
        },
        confirmAction() {
            if (this.confirmCallback) this.confirmCallback();
            this.showConfirmModal = false;
        },
        setLang(lang) {
            this.currentLang = lang;
            this.readerMode = false;
            this.analyzedSentences = [];
        },

        // --- ANALYSE & SAUVEGARDE DÉDIÉE ---
        openSaveModal() {
            if (!this.sourceText) return this.showToast("Rien à sauvegarder !");
            this.newAnalysisTitle = '';
            this.showSaveModal = true;
        },
        async confirmSaveAnalysis() {
            if (!this.newAnalysisTitle) return;
            try {
                await fetch('/lists/analyses/', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ title: this.newAnalysisTitle, content: this.sourceText, lang: this.currentLang })
                });
                this.showToast("Analyse sauvegardée !");
                this.showSaveModal = false;
            } catch(e) { this.showToast("Erreur sauvegarde"); }
        },
        async openLoadModal() {
            const res = await fetch('/lists/analyses/');
            this.savedAnalyses = await res.json();
            this.showLoadModal = true;
        },
        loadAnalysis(ana) {
            this.sourceText = ana.content;
            this.currentLang = ana.lang;
            this.showLoadModal = false;
            this.$nextTick(() => this.analyzeText());
        },
        deleteAnalysis(id) {
            this.triggerConfirm("Supprimer ce texte définitivement ?", async () => {
                await fetch(`/lists/analyses/${id}`, {method: 'DELETE'});
                this.openLoadModal(); // Rafraichir la liste
            });
        },

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
                    this.showToast("Erreur: " + err.detail);
                }
            } catch (e) { this.showToast("Erreur upload"); }
            finally { this.isLoading = false; event.target.value = ''; }
        },
        async analyzeText() {
            if (!this.sourceText) return;
            this.isLoading = true;
            try {
                const res = await fetch('/lists/analyze', { 
                    method: 'POST', headers: {'Content-Type': 'application/json'}, 
                    body: JSON.stringify({ text: this.sourceText, lang: this.currentLang }) 
                });
                const data = await res.json();
                this.analyzedSentences = data.sentences;
                this.readerMode = true; this.selectedToken = null;
            } catch (e) { this.showToast("Erreur analyse"); } finally { this.isLoading = false; }
        },
        selectToken(token, sentence) { this.selectedToken = token; this.currentContextSentence = sentence; },
        extractContextString(tokens) { return tokens ? tokens.map(t => t.text).join('') : ""; },
        getHighlightClass(token) {
            if (this.highlightLevel === 1 && (!token.jlpt || token.jlpt === 1)) return 'highlight-hard';
            return '';
        },
        async saveCurrentToken() {
            if (!this.selectedToken || !this.selectedListId) return this.showToast("Sélectionnez une liste !");
            const payload = [{
                terme: this.selectedToken.lemma, lecture: this.selectedToken.reading, pos: this.selectedToken.pos,
                ent_seq: this.selectedToken.ent_seq, definitions: this.selectedToken.definitions,
                context: this.extractContextString(this.currentContextSentence)
            }];
            try {
                const res = await fetch(`/lists/${this.selectedListId}/cards/bulk`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
                if (res.ok) this.showToast("Mot ajouté !");
            } catch (e) { this.showToast("Erreur"); }
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
            await fetch('/lists/', { 
                method: 'POST', headers: {'Content-Type': 'application/json'}, 
                body: JSON.stringify({ title: this.newListTitle, lang: this.currentLang }) 
            });
            this.newListTitle = ''; this.showCreateListModal = false; await this.fetchLists();
        },
        askDeleteCard(id) {
            // Optionnel: remettre confirmation si voulu, ici suppression directe silencieuse
             this.deleteCard(id); 
        },
        async deleteCard(id) {
            try { await fetch(`/lists/cards/${id}`, {method: 'DELETE'}); 
                if (this.activeList) this.activeList.cards = this.activeList.cards.filter(c => c.id !== id);
                this.showToast("Mot supprimé");
            } catch (e) {}
        },
        askDeleteList(list) {
            this.triggerConfirm(`Supprimer la liste "${list.title}" ?`, async () => {
                await fetch(`/lists/${list.id}`, {method: 'DELETE'});
                this.lists = this.lists.filter(l => l.id !== list.id);
                if (this.activeList && this.activeList.id === list.id) this.activeList = null;
                this.showToast("Liste supprimée");
            });
        },
        
        // --- TRAIN & DASH ---
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
            if(res.ok) { this.showToast("Import terminé"); this.fetchStats(); this.fetchLists(); }
        }
    }
}).mount('#app')