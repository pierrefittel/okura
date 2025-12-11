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
            
            // TRAINING (SRS)
            dueCards: [],
            currentCard: null,
            isFlipped: false, // Est-ce qu'on voit la réponse ?
            showCreateListModal: false,
            newListTitle: '',
            newListDesc: ''
        }
    },
    computed: {
        selectedCandidates() {
            return this.candidates ? this.candidates.filter(c => c.selected) : [];
        }
    },
    mounted() {
        this.fetchLists();
    },
    watch: {
        currentTab(newTab) {
            if (newTab === 'train') {
                this.startSession();
            }
        }
    },
    methods: {
        // --- TRAINING LOGIC ---
        
        async startSession() {
            this.currentCard = null;
            this.isFlipped = false;
            try {
                const res = await fetch('/lists/training/due');
                this.dueCards = await res.json();
                this.nextCard();
            } catch (e) {
                console.error("Erreur chargement session", e);
            }
        },

        nextCard() {
            if (this.dueCards.length > 0) {
                this.currentCard = this.dueCards[0];
                this.isFlipped = false;
            } else {
                this.currentCard = null; // Session finie
            }
        },

        flipCard() {
            this.isFlipped = true;
        },

        async submitReview(quality) {
            if (!this.currentCard) return;

            // Envoi de la note au serveur
            try {
                await fetch(`/lists/cards/${this.currentCard.id}/review`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ quality: quality })
                });

                // On retire la carte de la pile locale
                this.dueCards.shift();
                
                // Si c'était un échec (quality < 3), on pourrait vouloir la revoir tout de suite ?
                // Pour simplifier, on passe juste à la suivante.
                this.nextCard();

            } catch (e) {
                alert("Erreur de sauvegarde");
            }
        },

        // --- LISTS LOGIC ---
        
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
            } catch (e) { alert("Erreur chargement liste"); }
        },

        async deleteCard(cardId) {
            if (!confirm("Supprimer ?")) return;
            try {
                const res = await fetch(`/lists/cards/${cardId}`, { method: 'DELETE' }); // Note: URL corrigée avec préfixe /lists/ si nécessaire, vérifiez router
                if (res.ok) {
                   this.activeList.cards = this.activeList.cards.filter(c => c.id !== cardId);
                }
            } catch (e) { alert("Erreur"); }
        },

        async createNewList() {
            if (!this.newListTitle) return;
            try {
                const res = await fetch('/lists/', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ title: this.newListTitle, description: "Import" })
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

        // --- ANALYSE LOGIC ---

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
                terme: c.terme, lecture: c.lecture, pos: c.pos, ent_seq: c.ent_seq, definitions: c.definitions
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