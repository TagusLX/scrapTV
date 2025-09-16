document.addEventListener('DOMContentLoaded', function() {
    const apiBaseUrl = 'http://localhost:8000/api'; // This should be configurable
    const treeContainer = document.getElementById('is-zone-tree-container');
    const saveButton = document.getElementById('is-save-zones-button');

    let administrativeStructure = {};

    function buildTree(distritos) {
        let html = '<ul class="is-zone-tree">';
        distritos.forEach(distrito => {
            html += `
                <li>
                    <span class="is-tree-toggle">▶</span>
                    <input type="checkbox" class="is-zone-checkbox" data-level="distrito" data-id="${distrito.id}">
                    <label>${distrito.name_display}</label>
                    <ul class="is-nested-list" style="display: none;"></ul>
                </li>
            `;
        });
        html += '</ul>';
        treeContainer.innerHTML = html;
    }

    function loadChildren(element, level, ids) {
        const ul = element.querySelector('.is-nested-list');
        if (ul.innerHTML !== '') { // Already loaded
            ul.style.display = ul.style.display === 'none' ? 'block' : 'none';
            element.querySelector('.is-tree-toggle').textContent = ul.style.display === 'none' ? '▶' : '▼';
            return;
        }

        let url = '';
        if (level === 'distrito') {
            url = `${apiBaseUrl}/administrative/districts/${ids.distrito}/concelhos`;
        } else if (level === 'concelho') {
            url = `${apiBaseUrl}/administrative/districts/${ids.distrito}/concelhos/${ids.concelho}/freguesias`;
        } else {
            return;
        }

        fetch(url)
            .then(response => response.json())
            .then(data => {
                let items = [];
                if (level === 'distrito') items = data.concelhos;
                if (level === 'concelho') items = data.freguesias;

                let html = '';
                items.forEach(item => {
                    const nextLevel = level === 'distrito' ? 'concelho' : 'freguesia';
                    const hasChildren = nextLevel !== 'freguesia';
                    html += `
                        <li>
                            ${hasChildren ? '<span class="is-tree-toggle">▶</span>' : '<span class="is-tree-leaf"></span>'}
                            <input type="checkbox" class="is-zone-checkbox" data-level="${nextLevel}" data-distrito="${ids.distrito}" data-concelho="${ids.concelho || item.id}" data-id="${item.id}">
                            <label>${item.name_display}</label>
                            ${hasChildren ? '<ul class="is-nested-list" style="display: none;"></ul>' : ''}
                        </li>
                    `;
                });
                ul.innerHTML = html;
                ul.style.display = 'block';
                element.querySelector('.is-tree-toggle').textContent = '▼';
            })
            .catch(error => console.error(`Error fetching ${level}:`, error));
    }

    treeContainer.addEventListener('click', function(e) {
        if (e.target.classList.contains('is-tree-toggle')) {
            const li = e.target.parentElement;
            const checkbox = li.querySelector('.is-zone-checkbox');
            const level = checkbox.dataset.level;
            const ids = {
                distrito: checkbox.dataset.distrito || checkbox.dataset.id,
                concelho: checkbox.dataset.concelho
            };
            loadChildren(li, level, ids);
        } else if (e.target.type === 'checkbox') {
            const children = e.target.parentElement.querySelector('ul');
            if (children) {
                const checkboxes = children.querySelectorAll('input[type="checkbox"]');
                checkboxes.forEach(cb => cb.checked = e.target.checked);
            }
        }
    });

    // Initial load
    fetch(`${apiBaseUrl}/administrative/districts`)
        .then(response => response.json())
        .then(data => {
            if (data.districts) {
                buildTree(data.districts);
            }
        })
        .catch(error => console.error('Error fetching initial districts:', error));

    // Save button logic
    saveButton.addEventListener('click', function() {
        const selectedZones = [];
        const checkboxes = treeContainer.querySelectorAll('.is-zone-checkbox:checked');
        checkboxes.forEach(cb => {
            selectedZones.push({
                level: cb.dataset.level,
                id: cb.dataset.id,
                distrito: cb.dataset.distrito,
                concelho: cb.dataset.concelho
            });
        });

        // We need an AJAX handler for this
        const nonce = document.getElementById('is_nonce').value;
        const data = new URLSearchParams();
        data.append('action', 'save_selected_zones');
        data.append('nonce', nonce);
        data.append('selected_zones', JSON.stringify(selectedZones));

        fetch(ajaxurl, {
            method: 'POST',
            body: data
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                alert(result.data);
            } else {
                alert('Error: ' + result.data);
            }
        })
        .catch(error => {
            console.error('Error saving zones:', error);
            alert('An error occurred while saving.');
        });
    });

    // Add some basic styling
    const style = document.createElement('style');
    style.textContent = `
        .is-zone-tree, .is-nested-list { list-style: none; padding-left: 20px; }
        .is-tree-toggle { cursor: pointer; }
        .is-tree-leaf { display: inline-block; width: 1em; }
    `;
    document.head.appendChild(style);
});
