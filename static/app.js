const { createApp } = Vue

createApp({
    data() {
        return {
            currentTab: 'analyze',
            
            // ANALYSE / READER
            sourceText: '',
            readerMode: false,
            isLoading: false,
            analyzedSentences: [], // Structure [[token, token], [token...]]
            
            selectedToken: null,
            currentContextSentence: [], // La phrase entière du mot sélectionné
            highlightLevel: 0, // Filtre visuel

            // LISTES
            lists: [],
            selectedListId: null,
            activeList: null,
            showCreateListModal: false,
            newListTitle: '',
            
            // TRAIN & DASH
            dueCards: [],
            currentCard: null,
            isFlipped: false,
            stats: { total_cards: 0, cards_learned: 0, due_today: 0, heatmap: {} }
        }
    },
    mounted() {
        this.fetchLists();
        this.fetchStats();
    },
    watch: {
        currentTab(newTab) {
            if (newTab === 'train') this.startSession();
            if (newTab === 'dashboard') this.fetchStats();
        }
    },
    methods: {
        // --- READER LOGIC ---
        
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
                this.analyzedSentences = data.sentences;
                this.readerMode = true; // Bascule en mode lecture
                this.selectedToken = null;
            } catch (e) { alert("Erreur analyse"); }
            finally { this.isLoading = false; }
        },

        selectToken(token, sentence) {
            this.selectedToken = token;
            this.currentContextSentence = sentence;
        },

        extractContextString(sentenceTokens) {
            if (!sentenceTokens) return "";
            // Reconstruit la phrase string à partir des tokens
            return sentenceTokens.map(t => t.text).join('');
        },

        getHighlightClass(token) {
            if (this.highlightLevel === 0) return '';
            
            // Mode "Surligner Difficiles" (N1 ou inconnu)
            if (this.highlightLevel === 1) {
                if (!token.jlpt || token.jlpt === 1) return 'highlight-hard';
            }
            // Mode "Surligner Faciles" (N4/N5)
            if (this.highlightLevel === 4) {
                if (token.jlpt >= 4) return 'highlight-easy';
            }
            return '';
        },

        async saveCurrentToken() {
            if (!this.selectedToken || !this.selectedListId) return;
            
            // Construction de la payload pour l'API Bulk (on envoie une liste de 1)
            const payload = [{
                terme: this.selectedToken.lemma,
                lecture: this.selectedToken.reading,
                pos: this.selectedToken.pos,
                ent_seq: this.selectedToken.ent_seq,
                definitions: this.selectedToken.definitions,
                context: this.extractContextString(this.currentContextSentence)
            }];

            try {
                const res = await fetch(`/lists/${this.selectedListId}/cards/bulk`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    alert("Mot sauvegardé !");
                    // Feedback visuel ? Peut-être marquer le mot comme "sauvegardé" dans le texte
                }
            } catch (e) { alert("Erreur sauvegarde"); }
        },

        // --- COMMON LOGIC (Identique avant) ---
        async fetchLists() {
            const res = await fetch('/lists/');
            this.lists = await res.json();
            if (this.lists.length > 0 && !this.selectedListId) this.selectedListId = this.lists[this.lists.length-1].id;
        },
        async openList(list) {
            const res = await fetch(`/lists/${list.id}`);
            this.activeList = await res.json();
        },
        async createNewList() {
            await fetch('/lists/', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ title: this.newListTitle })
            });
            await this.fetchLists();
            this.showCreateListModal = false;
        },
        async deleteCard(id) {
            if(confirm("Supprimer?")) {
                await fetch(`/lists/cards/${id}`, {method: 'DELETE'});
                this.activeList.cards = this.activeList.cards.filter(c => c.id !== id);
            }
        },
        // TRAIN
        async startSession() {
            const res = await fetch('/lists/training/due');
            this.dueCards = await res.json();
            this.nextCard();
        },
        nextCard() {
            this.currentCard = this.dueCards.length ? this.dueCards[0] : null;
            this.isFlipped = false;
        },
        flipCard() { this.isFlipped = true; },
        async submitReview(q) {
            await fetch(`/lists/cards/${this.currentCard.id}/review`, {
                method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({quality: q})
            });
            this.dueCards.shift();
            this.nextCard();
        },
        // DASH
        async fetchStats() {
            const res = await fetch('/lists/dashboard/stats');
            this.stats = await res.json();
        }
    }
}).mount('#app')