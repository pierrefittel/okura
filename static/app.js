const { createApp } = Vue

createApp({
    data() {
        return {
            currentTab: 'analyze',
            sourceText: '',
            lists: [],
            selectedListId: null,
            candidates: [], // Les mots trouvés par l'analyseur
            
            // Modal
            showCreateListModal: false,
            newListTitle: ''
        }
    },
    computed: {
        selectedCandidates() {
            return this.candidates.filter(c => c.selected);
        }
    },
    mounted() {
        this.fetchLists();
    },
    methods: {
        async fetchLists() {
            try {
                const res = await fetch('/lists/');
                this.lists = await res.json();
                // Sélectionne la dernière liste par défaut si dispo
                if (this.lists.length > 0 && !this.selectedListId) {
                    this.selectedListId = this.lists[this.lists.length - 1].id;
                }
            } catch (e) {
                console.error("Erreur chargement listes", e);
            }
        },

        async analyzeText() {
            if (!this.sourceText) return;
            
            // 1. Appel API Analyse
            const res = await fetch('/lists/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ text: this.sourceText })
            });
            const data = await res.json();
            
            // 2. Transformation pour le frontend (ajout propriété 'selected')
            this.candidates = data.candidates.map(c => ({
                ...c,
                selected: false // Par défaut, rien n'est coché (ou true si vous préférez)
            }));
        },

        toggleWord(word) {
            word.selected = !word.selected;
        },

        async createNewList() {
            if (!this.newListTitle) return;
            
            const res = await fetch('/lists/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ title: this.newListTitle, description: "Créée depuis l'analyseur" })
            });
            
            if (res.ok) {
                await this.fetchLists();
                const newList = await res.json(); // On devrait récupérer la nouvelle liste ici
                this.selectedListId = this.lists[this.lists.length - 1].id; // Hack rapide pour sélectionner la dernière
                this.showCreateListModal = false;
                this.newListTitle = '';
            }
        },

        async saveSelection() {
            if (!this.selectedListId || this.selectedCandidates.length === 0) return;

            const payload = this.selectedCandidates.map(c => ({
                terme: c.terme,
                lecture: c.lecture,
                pos: c.pos,
                ent_seq: c.ent_seq,
                definitions: c.definitions
            }));

            // Appel de la route BULK créée précédemment
            const res = await fetch(`/lists/${this.selectedListId}/cards/bulk`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                alert(`${payload.length} mots importés avec succès !`);
                // Optionnel: vider la sélection
                this.candidates.forEach(c => c.selected = false);
            } else {
                alert("Erreur lors de l'import.");
            }
        },
        
        formatDefs(defs) {
            return defs.join('\n');
        }
    }
}).mount('#app')