document.addEventListener('DOMContentLoaded', function() {
    // Use the localized URL provided by WordPress
    const apiBaseUrl = is_market_data_config.backend_url + '/api';

    const distritoSelect = document.getElementById('is-distrito-select');
    const concelhoSelect = document.getElementById('is-concelho-select');
    const freguesiaSelect = document.getElementById('is-freguesia-select');
    const formContainer = document.getElementById('is-market-data-form-container');

    // Fetch and populate Distritos
    fetch(`${apiBaseUrl}/administrative/districts`)
        .then(response => response.json())
        .then(data => {
            if (data.districts) {
                data.districts.forEach(distrito => {
                    const option = document.createElement('option');
                    option.value = distrito.id;
                    option.textContent = distrito.name_display;
                    distritoSelect.appendChild(option);
                });
            }
        })
        .catch(error => console.error('Error fetching distritos:', error));

    // Event listener for Distrito select
    distritoSelect.addEventListener('change', function() {
        const distritoId = this.value;
        resetSelect(concelhoSelect, 'Select a Concelho');
        resetSelect(freguesiaSelect, 'Select a Freguesia');
        concelhoSelect.disabled = true;
        freguesiaSelect.disabled = true;
        formContainer.style.display = 'none';

        if (distritoId) {
            fetch(`${apiBaseUrl}/administrative/districts/${distritoId}/concelhos`)
                .then(response => response.json())
                .then(data => {
                    if (data.concelhos) {
                        data.concelhos.forEach(concelho => {
                            const option = document.createElement('option');
                            option.value = concelho.id;
                            option.textContent = concelho.name_display;
                            concelhoSelect.appendChild(option);
                        });
                        concelhoSelect.disabled = false;
                    }
                })
                .catch(error => console.error('Error fetching concelhos:', error));

            fetchMarketData(distritoId);
        }
    });

    // Event listener for Concelho select
    concelhoSelect.addEventListener('change', function() {
        const distritoId = distritoSelect.value;
        const concelhoId = this.value;
        resetSelect(freguesiaSelect, 'Select a Freguesia');
        freguesiaSelect.disabled = true;
        formContainer.style.display = 'none';

        if (concelhoId) {
            fetch(`${apiBaseUrl}/administrative/districts/${distritoId}/concelhos/${concelhoId}/freguesias`)
                .then(response => response.json())
                .then(data => {
                    if (data.freguesias) {
                        data.freguesias.forEach(freguesia => {
                            const option = document.createElement('option');
                            option.value = freguesia.id;
                            option.textContent = freguesia.name_display;
                            freguesiaSelect.appendChild(option);
                        });
                        freguesiaSelect.disabled = false;
                    }
                })
                .catch(error => console.error('Error fetching freguesias:', error));

            fetchMarketData(distritoId, concelhoId);
        } else {
            fetchMarketData(distritoId);
        }
    });

    // Event listener for Freguesia select
    freguesiaSelect.addEventListener('change', function() {
        const distritoId = distritoSelect.value;
        const concelhoId = concelhoSelect.value;
        const freguesiaId = this.value;
        formContainer.style.display = 'none';

        if (freguesiaId) {
            fetchMarketData(distritoId, concelhoId, freguesiaId);
        } else {
            fetchMarketData(distritoId, concelhoId);
        }
    });

    function fetchMarketData(distrito, concelho = null, freguesia = null) {
        let url = `${apiBaseUrl}/market-data?distrito=${distrito}`;
        if (concelho) {
            url += `&concelho=${concelho}`;
        }
        if (freguesia) {
            url += `&freguesia=${freguesia}`;
        }

        fetch(url)
            .then(response => response.json())
            .then(data => {
                console.log('Market data fetched:', data);
                renderForm(data, distrito, concelho, freguesia);
            })
            .catch(error => console.error('Error fetching market data:', error));
    }

    function renderForm(data, distrito, concelho, freguesia) {
        let formHtml = '<form id="is-market-data-form">';
        formHtml += '<h2>Market Data</h2>';
        formHtml += '<table class="form-table">';

        for (const key in data) {
            if (typeof data[key] !== 'object') {
                const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                const type = (typeof data[key] === 'number') ? 'number' : 'text';
                formHtml += `
                    <tr>
                        <th scope="row"><label for="is-field-${key}">${label}</label></th>
                        <td><input type="${type}" id="is-field-${key}" name="${key}" value="${data[key]}" class="regular-text"></td>
                    </tr>
                `;
            }
        }

        formHtml += '</table>';
        formHtml += '<h3>Manual Scrape</h3>';
        formHtml += '<table class="form-table">';
        formHtml += `
            <tr>
                <th scope="row"><label for="is-manual-url">Manual Scrape URL</label></th>
                <td>
                    <input type="url" id="is-manual-url" name="manual_url" value="${data.manual_url || ''}" class="regular-text" style="width: 70%;">
                    <button type="button" id="is-scrape-manual-url" class="button">Scrape & Update Price</button>
                    <div id="manual-scrape-status" style="margin-top: 5px; font-style: italic;"></div>
                </td>
            </tr>
        `;
        formHtml += '</table>';

        formHtml += '<p class="submit"><input type="submit" name="submit" id="submit" class="button button-primary" value="Save All Changes"></p>';
        formHtml += '</form>';

        formContainer.innerHTML = formHtml;
        formContainer.style.display = 'block';

        const form = document.getElementById('is-market-data-form');
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            saveMarketData(this, distrito, concelho, freguesia);
        });

        const scrapeButton = document.getElementById('is-scrape-manual-url');
        scrapeButton.addEventListener('click', function() {
            const manualUrl = document.getElementById('is-manual-url').value;
            if (!manualUrl) {
                alert('Please enter a URL to scrape.');
                return;
            }

            const statusDiv = document.getElementById('manual-scrape-status');
            statusDiv.textContent = 'Scraping...';
            this.disabled = true;

            // This new endpoint will need to be created in the backend
            fetch(`${apiBaseUrl}/scrape/manual-url`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    distrito: distrito,
                    concelho: concelho,
                    freguesia: freguesia,
                    manual_url: manualUrl
                })
            })
            .then(response => response.json())
            .then(result => {
                statusDiv.textContent = result.message || 'Done.';
                if (result.new_price !== undefined) {
                    // Update the price in the form field visually
                    document.querySelector('[name="average"]').value = result.new_price;
                }
                scrapeButton.disabled = false;
            })
            .catch(error => {
                console.error('Error scraping manual URL:', error);
                statusDiv.textContent = 'An error occurred during scraping.';
                scrapeButton.disabled = false;
            });
        });
    }

    function saveMarketData(form, distrito, concelho, freguesia) {
        const formData = new FormData(form);
        const data = {};
        for (const [key, value] of formData.entries()) {
            // Check if the value is a number string and convert it
            if (!isNaN(value) && value.trim() !== '') {
                data[key] = Number(value);
            } else {
                data[key] = value;
            }
        }

        let url = `${apiBaseUrl}/market-data?distrito=${distrito}`;
        if (concelho) {
            url += `&concelho=${concelho}`;
        }
        if (freguesia) {
            url += `&freguesia=${freguesia}`;
        }

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if (result.message) {
                alert(result.message);
            } else {
                alert('An error occurred.');
            }
        })
        .catch(error => {
            console.error('Error saving market data:', error);
            alert('An error occurred while saving.');
        });
    }

    function resetSelect(selectElement, defaultText) {
        selectElement.innerHTML = `<option value="">${defaultText}</option>`;
    }
});
