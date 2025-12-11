const { createApp } = Vue

createApp({
    data() {
        return {
            currentTab: 'analyze',
            sourceText: '',
            isLoading: false,
            
            lists: [],
            candidates: [],
            
            selectedListId: null,
            showModal: false,
            newListTitle: '',
            newListDesc: '',

            // --- NOUVEAU ---
            activeList: null // Stocke la liste en cours de consultation
        }
    },
    // ... computed et mounted inchangés ...
    mounted() {
        this.fetchLists()
    },
    methods: {
        // ... méthodes existantes (fetchLists, analyzeText, createList...) ...

        // --- NOUVELLES MÉTHODES À AJOUTER ---
        
        async openList(list) {
            // On appelle l'API pour avoir le détail (les cartes)
            try {
                const res = await fetch(`/lists/${list.id}`);
                this.activeList = await res.json();
            } catch (e) {
                alert("Impossible de charger la liste");
            }
        },

        async deleteCard(cardId) {
            if (!confirm("Supprimer ce mot de la liste ?")) return;

            try {
                const res = await fetch(`/cards/${cardId}`, { method: 'DELETE' });
                if (res.ok) {
                    // Mise à jour locale (retire l'élément du tableau sans recharger)
                    this.activeList.cards = this.activeList.cards.filter(c => c.id !== cardId);
                }
            } catch (e) {
                alert("Erreur lors de la suppression");
            }
        },
        // ... (Re-collez les anciennes méthodes importSelection, formatDefs ici si besoin)
        // Note: Assurez-vous de bien garder importSelection !
        async importSelection() {
             // (Code existant inchangé)
             if (!this.selectedListId) return
             // ...
             // Le reste de votre fonction importSelection...
             const payload = this.selectedCandidates.map(c => ({
                terme: c.terme,
                lecture: c.lecture,
                pos: c.pos,
                ent_seq: c.ent_seq,
                definitions: c.definitions
            }))

            try {
                const res = await fetch(`/lists/${this.selectedListId}/cards/bulk`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                })

                if (res.ok) {
                    this.candidates.forEach(c => {
                        if (c.selected) c.selected = false
                    })
                    alert(`${payload.length} mots ajoutés à la liste !`)
                } else {
                    alert("Erreur lors de l'import (Problème serveur)")
                }
            } catch (e) {
                alert("Erreur réseau")
            }
        }, 
        // ...
        async createNewList() {
             // (Code existant inchangé, attention j'ai vu createList vs createNewList, gardez celui qui marche)
             // Dans votre dernier fichier uploadé c'était createNewList, dans mon code précédent createList. 
             // Gardez la cohérence avec votre HTML (@click="createNewList")
             if (!this.newListTitle) return;
             // ... code existant ...
             const res = await fetch('/lists/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ title: this.newListTitle, description: "Créée depuis l'analyseur" })
            });
            
            if (res.ok) {
                await this.fetchLists();
                const newList = await res.json(); 
                this.selectedListId = this.lists[this.lists.length - 1].id;
                this.showCreateListModal = false; // Attention au nom de variable (showCreateListModal vs showModal)
                this.newListTitle = '';
            }
        },
        async analyzeText() {
            // (Code existant inchangé)
             if (!this.sourceText) return;
            // ...
            const res = await fetch('/lists/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ text: this.sourceText })
            });
            const data = await res.json();
            this.candidates = data.candidates.map(c => ({
                ...c,
                selected: false 
            }));
        },
        toggleWord(word) {
            word.selected = !word.selected;
        },
        formatDefs(defs) {
            return defs.join('\n');
        }
    }
}).mount('#app')