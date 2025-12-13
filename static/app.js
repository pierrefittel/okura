const { createApp } = Vue

createApp({
    data() {
        return {
            // État principal
            currentTab: 'analyze',
            currentLang: 'jp',
            sourceText: '', 
            readerMode: false, 
            isLoading: false, // <-- Pour l'animation de chargement
            analyzedSentences: [],
            selectedToken: null, 
            currentContextSentence: [], 
            highlightLevel: 0,
            
            // Données
            lists: [], selectedListId: null, activeList: null, 
            dueCards: [], currentCard: null, isFlipped: false, trainListId: null,
            savedAnalyses: [],
            stats: { total_cards: 0, cards_learned: 0, due_today: 0, heatmap: {} },
            
            // Modales & UI
            toastMessage: '',
            showCreateListModal: false, newListTitle: '',
            showSaveModal: false, newAnalysisTitle: '',
            showLoadModal: false, 
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
        showToast(msg) { this.toastMessage = msg; setTimeout(() => this.toastMessage = '', 3000); },
        triggerConfirm(msg, cb) { this.confirmMessage = msg; this.confirmCallback = cb; this.showConfirmModal = true; },
        confirmAction() { if(this.confirmCallback) this.confirmCallback(); this.showConfirmModal = false; },
        
        setLang(l) { 
            this.currentLang = l; 
            // On ne reset pas tout de suite le readerMode pour garder le texte affiché
            // Mais on relance l'analyse si du texte est présent
            if (this.sourceText) this.analyzeText();
        },

        // --- CORE: ANALYSE ---
        async analyzeText() {
            if (!this.sourceText) return;
            this.isLoading = true; // Active l'animation
            try {
                const res = await fetch('/lists/analyze', { 
                    method: 'POST', 
                    headers: {'Content-Type': 'application/json'}, 
                    body: JSON.stringify({ text: this.sourceText, lang: this.currentLang }) 
                });
                if(res.ok) {
                    const data = await res.json();
                    this.analyzedSentences = data.sentences;
                    this.readerMode = true; 
                    this.selectedToken = null;
                }
            } catch (e) { this.showToast("Erreur analyse"); } 
            finally { this.isLoading = false; } // Désactive l'animation
        },

        async uploadTextFile(event) {
            const file = event.target.files[0];
            if (!file) return;
            this.isLoading = true;
            const formData = new FormData();
            formData.append('file', file);
            formData.append('lang', this.currentLang); // Envoie la langue actuelle
            
            try {
                const res = await fetch('/lists/analyze/file', { method: 'POST', body: formData });
                if (res.ok) {
                    const data = await res.json();
                    this.analyzedSentences = data.sentences;
                    this.sourceText = data.raw_text; // <-- CRUCIAL: Remplit la zone de texte pour la sauvegarde
                    this.readerMode = true; 
                    this.selectedToken = null;
                } else {
                    const err = await res.json();
                    this.showToast("Erreur: " + err.detail);
                }
            } catch (e) { this.showToast("Erreur upload"); }
            finally { this.isLoading = false; event.target.value = ''; }
        },

        // --- SAUVEGARDE & CHARGEMENT (DEDIES) ---
        openSaveModal() {
            if (!this.sourceText) return this.showToast("Rien à sauvegarder");
            this.newAnalysisTitle = '';
            this.showSaveModal = true;
        },
        async confirmSaveAnalysis() {
            if (!this.newAnalysisTitle) return;
            try {
                // Sauvegarde dans la table 'analyses'
                const res = await fetch('/lists/analyses/', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ title: this.newAnalysisTitle, content: this.sourceText, lang: this.currentLang })
                });
                if(res.ok) { this.showToast("Sauvegardé !"); this.showSaveModal = false; }
                else throw new Error();
            } catch(e) { this.showToast("Erreur sauvegarde (BDD non mise à jour?)"); }
        },
        async openLoadModal() {
            try {
                const res = await fetch('/lists/analyses/');
                if(res.ok) { this.savedAnalyses = await res.json(); this.showLoadModal=true; }
            } catch(e) { this.showToast("Erreur chargement"); }
        },
        loadAnalysis(ana) {
            this.sourceText = ana.content;
            this.currentLang = ana.lang || 'jp';
            this.showLoadModal = false;
            // On attend que le DOM soit prêt pour relancer l'analyse
            this.$nextTick(() => this.analyzeText());
        },
        deleteAnalysis(id) {
            this.triggerConfirm("Supprimer ce texte ?", async () => {
                await fetch(`/lists/analyses/${id}`, {method: 'DELETE'});
                this.openLoadModal(); // Rafraichir la liste
            });
        },
        // Compatibilité avec les anciennes listes qui contiennent du texte
        loadTextFromList(list) {
            if (list.source_text) {
                this.sourceText = list.source_text;
                this.currentLang = list.lang || 'jp';
                this.currentTab = 'analyze';
                this.$nextTick(() => this.analyzeText());
            }
        },

        // --- INTERACTIONS MOTS ---
        selectToken(token, sentence) { this.selectedToken = token; this.currentContextSentence = sentence; },
        extractContextString(tokens) { return tokens ? tokens.map(t => t.text).join('') : ""; },
        getHighlightClass(token) { return (this.highlightLevel===1 && (!token.jlpt || token.jlpt===1)) ? 'highlight-hard' : ''; },
        async saveCurrentToken() {
            if (!this.selectedToken || !this.selectedListId) return this.showToast("Sélectionnez une liste");
            const p = [{
                terme:this.selectedToken.lemma, lecture:this.selectedToken.reading, pos:this.selectedToken.pos,
                ent_seq:this.selectedToken.ent_seq, definitions:this.selectedToken.definitions,
                context:this.extractContextString(this.currentContextSentence)
            }];
            try {
                const res = await fetch(`/lists/${this.selectedListId}/cards/bulk`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(p)});
                if(res.ok) this.showToast("Mot ajouté");
            } catch(e) { this.showToast("Erreur ajout"); }
        },

        // --- LISTES & CRUD ---
        async fetchLists() { const r=await fetch('/lists/'); this.lists=await r.json(); if(!this.selectedListId && this.lists.length) this.selectedListId=this.lists[this.lists.length-1].id; },
        async openList(l) { const r=await fetch(`/lists/${l.id}`); this.activeList=await r.json(); },
        async createNewList() {
            if(!this.newListTitle) return;
            try { 
                await fetch('/lists/', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({title:this.newListTitle, lang:this.currentLang})});
                this.newListTitle=''; this.showCreateListModal=false; this.fetchLists(); 
            } catch(e) { this.showToast("Erreur"); }
        },
        askDeleteCard(id) {
            this.triggerConfirm("Supprimer ce mot ?", async () => {
                await fetch(`/lists/cards/${id}`, {method:'DELETE'});
                if(this.activeList) this.activeList.cards = this.activeList.cards.filter(c => c.id !== id);
                this.showToast("Mot supprimé");
            });
        },
        askDeleteList(l) {
            this.triggerConfirm(`Supprimer la liste "${l.title}" ?`, async () => {
                await fetch(`/lists/${l.id}`, {method:'DELETE'});
                this.lists = this.lists.filter(x => x.id !== l.id);
                if(this.activeList && this.activeList.id === l.id) this.activeList=null;
                this.showToast("Liste supprimée");
            });
        },

        // --- TRAIN & DATA ---
        async startSession() { let u='/lists/training/due'; if(this.trainListId) u+=`?list_id=${this.trainListId}`; const r=await fetch(u); this.dueCards=await r.json(); this.nextCard(); },
        nextCard() { this.currentCard=this.dueCards.length?this.dueCards[0]:null; this.isFlipped=false; },
        flipCard() { this.isFlipped=true; },
        async submitReview(q) { await fetch(`/lists/cards/${this.currentCard.id}/review`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({quality:q})}); this.dueCards.shift(); this.nextCard(); },
        async fetchStats() { const r=await fetch('/lists/dashboard/stats'); this.stats=await r.json(); },
        getHeatClass(c) { if(!c)return ''; if(c<=5)return 'heat-1'; return 'heat-4'; },
        downloadCsv() { window.location.href="/lists/data/export"; },
        async uploadCsv(e) { const f=e.target.files[0]; if(!f)return; const d=new FormData(); d.append('file',f); const r=await fetch('/lists/data/import',{method:'POST',body:d}); if(r.ok){this.showToast("Import OK"); this.fetchStats(); this.fetchLists();} }
    }
}).mount('#app')