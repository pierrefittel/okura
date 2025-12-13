const { createApp } = Vue

createApp({
    data() {
        return {
            currentTab: 'analyze',
            currentLang: 'jp',
            sourceText: '', 
            readerMode: false, 
            isLoading: false, 
            analyzedSentences: [],
            selectedToken: null, 
            currentContextSentence: [], 
            highlightLevel: 0,
            
            lists: [], selectedListId: null, activeList: null, 
            dueCards: [], currentCard: null, isFlipped: false, trainListId: null,
            
            // UI States
            toastMessage: '',
            showCreateListModal: false, newListTitle: '',
            showSaveModal: false, newAnalysisTitle: '',
            showLoadModal: false, savedAnalyses: [],
            showConfirmModal: false, confirmMessage: '', confirmCallback: null,
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
        // --- UTILS ---
        showToast(msg) { this.toastMessage = msg; setTimeout(() => this.toastMessage = '', 3000); },
        triggerConfirm(msg, cb) { this.confirmMessage = msg; this.confirmCallback = cb; this.showConfirmModal = true; },
        confirmAction() { if(this.confirmCallback) this.confirmCallback(); this.showConfirmModal = false; },
        
        setLang(l) { 
            this.currentLang = l; 
            // Si on a déjà du texte, on le réanalyse dans la nouvelle langue
            if (this.sourceText) this.analyzeText();
        },

        // --- ANALYSE ---
        async analyzeText() {
            if (!this.sourceText) return;
            this.isLoading = true;
            this.analyzedSentences = []; // Reset visuel
            
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
                } else {
                    this.showToast("Erreur serveur lors de l'analyse");
                }
            } catch (e) { 
                console.error(e);
                this.showToast("Erreur réseau"); 
            } finally { 
                this.isLoading = false; 
            }
        },

        async uploadTextFile(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            this.isLoading = true;
            const formData = new FormData();
            formData.append('file', file);
            formData.append('lang', this.currentLang);
            
            try {
                const res = await fetch('/lists/analyze/file', { method: 'POST', body: formData });
                if (res.ok) {
                    const data = await res.json();
                    // On met à jour le texte source ET le résultat
                    this.sourceText = data.raw_text; 
                    this.analyzedSentences = data.sentences;
                    this.readerMode = true;
                    this.selectedToken = null;
                    this.showToast("Fichier chargé et analysé");
                } else {
                    const err = await res.json();
                    this.showToast("Erreur: " + (err.detail || "Fichier invalide"));
                }
            } catch (e) { this.showToast("Erreur upload"); }
            finally { this.isLoading = false; event.target.value = ''; }
        },

        // --- SAVE / LOAD ANALYSES ---
        openSaveModal() {
            if (!this.sourceText) return this.showToast("Rien à sauvegarder");
            this.newAnalysisTitle = '';
            this.showSaveModal = true;
        },
        async confirmSaveAnalysis() {
            if (!this.newAnalysisTitle) return;
            try {
                const res = await fetch('/lists/analyses/', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ 
                        title: this.newAnalysisTitle, 
                        content: this.sourceText, 
                        lang: this.currentLang 
                    })
                });
                if(res.ok) { 
                    this.showToast("Analyse sauvegardée !"); 
                    this.showSaveModal = false; 
                } else {
                    this.showToast("Erreur technique (BDD)");
                }
            } catch(e) { this.showToast("Erreur réseau"); }
        },
        async openLoadModal() {
            try {
                const res = await fetch('/lists/analyses/');
                if(res.ok) { 
                    this.savedAnalyses = await res.json(); 
                    this.showLoadModal = true; 
                }
            } catch(e) { this.showToast("Erreur chargement liste"); }
        },
        loadAnalysis(ana) {
            this.sourceText = ana.content;
            this.currentLang = ana.lang || 'jp';
            this.showLoadModal = false;
            
            // On force le mode éditeur d'abord pour être sûr
            this.readerMode = false;
            
            // Puis on lance l'analyse après un court délai pour que Vue mette à jour l'état
            setTimeout(() => {
                this.analyzeText();
            }, 100);
        },
        deleteAnalysis(id) {
            this.triggerConfirm("Supprimer définitivement ce texte ?", async () => {
                await fetch(`/lists/analyses/${id}`, {method: 'DELETE'});
                this.openLoadModal(); // Rafraichir la liste
            });
        },

        // --- LISTES, CARDS, TRAIN (Standard) ---
        async fetchLists() { const r=await fetch('/lists/'); this.lists=await r.json(); if(!this.selectedListId && this.lists.length) this.selectedListId=this.lists[this.lists.length-1].id; },
        async openList(l) { const r=await fetch(`/lists/${l.id}`); this.activeList=await r.json(); },
        async createNewList() {
            if(!this.newListTitle) return;
            try { await fetch('/lists/', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({title:this.newListTitle, lang:this.currentLang})}); this.newListTitle=''; this.showCreateListModal=false; this.fetchLists(); } catch(e) {}
        },
        askDeleteCard(id) { this.triggerConfirm("Supprimer ce mot ?", () => this.deleteCard(id)); },
        async deleteCard(id) { try { await fetch(`/lists/cards/${id}`, {method:'DELETE'}); if(this.activeList) this.activeList.cards = this.activeList.cards.filter(c => c.id !== id); this.showToast("Mot supprimé"); } catch(e){} },
        askDeleteList(l) { this.triggerConfirm(`Supprimer "${l.title}" ?`, async () => { await fetch(`/lists/${l.id}`, {method:'DELETE'}); this.lists = this.lists.filter(x => x.id !== l.id); if(this.activeList && this.activeList.id === l.id) this.activeList=null; this.showToast("Liste supprimée"); }); },
        
        selectToken(t,s) { this.selectedToken=t; this.currentContextSentence=s; },
        extractContextString(tokens) { return tokens ? tokens.map(t => t.text).join('') : ""; },
        getHighlightClass(token) { return (this.highlightLevel===1 && (!token.jlpt || token.jlpt===1)) ? 'highlight-hard' : ''; },
        async saveCurrentToken() {
            if (!this.selectedToken || !this.selectedListId) return this.showToast("Sélectionnez une liste");
            const p = [{terme:this.selectedToken.lemma, lecture:this.selectedToken.reading, pos:this.selectedToken.pos, ent_seq:this.selectedToken.ent_seq, definitions:this.selectedToken.definitions, context:this.extractContextString(this.currentContextSentence)}];
            try { const r = await fetch(`/lists/${this.selectedListId}/cards/bulk`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(p)}); if(r.ok) this.showToast("Mot ajouté !"); } catch(e) { this.showToast("Erreur"); }
        },
        
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