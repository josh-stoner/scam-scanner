(function () {
    "use strict";

    // Submit form handler
    var submitForm = document.getElementById("submit-form");
    var formSuccess = document.getElementById("form-success");
    if (submitForm) {
        submitForm.addEventListener("submit", function () {
            setTimeout(function () {
                submitForm.style.display = "none";
                formSuccess.style.display = "block";
            }, 500);
        });
    }

    let allProducts = [];
    let currentFilter = "all";
    let currentSearch = "";
    let currentSort = "score-asc";

    const grid = document.getElementById("product-grid");
    const searchInput = document.getElementById("search");
    const sortSelect = document.getElementById("sort-select");
    const resultsCount = document.getElementById("results-count");
    const template = document.getElementById("product-card-template");

    // Fetch data
    fetch("data.json")
        .then(function (r) { return r.json(); })
        .then(function (data) {
            allProducts = data.products;
            renderStats(data);
            render();
        })
        .catch(function () {
            grid.textContent = "";
            var msg = document.createElement("div");
            msg.className = "no-results";
            var p = document.createElement("p");
            p.textContent = "Failed to load product database.";
            msg.appendChild(p);
            grid.appendChild(msg);
        });

    // Event listeners
    searchInput.addEventListener("input", function (e) {
        currentSearch = e.target.value.toLowerCase().trim();
        render();
    });

    sortSelect.addEventListener("change", function (e) {
        currentSort = e.target.value;
        render();
    });

    document.querySelector(".filters").addEventListener("click", function (e) {
        if (!e.target.classList.contains("filter-btn")) return;
        document.querySelectorAll(".filter-btn").forEach(function (b) { b.classList.remove("active"); });
        e.target.classList.add("active");
        currentFilter = e.target.dataset.filter;
        render();
    });

    function renderStats(data) {
        document.getElementById("stat-total").textContent = data.total;
        document.getElementById("stat-avg-score").textContent = data.average_score;

        var scamCount = (data.by_verdict["SCAM"] || 0) + (data.by_verdict["LIKELY SCAM"] || 0);
        var cautionCount = data.by_verdict["CAUTION"] || 0;
        document.getElementById("stat-scam").textContent = scamCount;
        document.getElementById("stat-caution").textContent = cautionCount;
    }

    function filterProducts() {
        var filtered = allProducts;

        if (currentFilter !== "all") {
            filtered = filtered.filter(function (p) { return p.verdict === currentFilter; });
        }

        if (currentSearch) {
            filtered = filtered.filter(function (p) {
                var haystack = [
                    p.product_name,
                    p.category,
                    p.domain,
                    p.verdict
                ].concat(p.red_flags, p.claims_extracted).join(" ").toLowerCase();
                return haystack.includes(currentSearch);
            });
        }

        filtered.sort(function (a, b) {
            switch (currentSort) {
                case "score-asc": return a.trust_score - b.trust_score;
                case "score-desc": return b.trust_score - a.trust_score;
                case "name-asc": return a.product_name.localeCompare(b.product_name);
                case "date-desc": return b.date_evaluated.localeCompare(a.date_evaluated);
                default: return 0;
            }
        });

        return filtered;
    }

    function verdictClass(verdict) {
        switch (verdict) {
            case "SCAM": return "verdict-scam";
            case "LIKELY SCAM": return "verdict-likely-scam";
            case "CAUTION": return "verdict-caution";
            case "LEGIT": return "verdict-legit";
            default: return "";
        }
    }

    function scoreClass(score) {
        if (score >= 70) return "score-green";
        if (score >= 40) return "score-yellow";
        if (score >= 20) return "score-orange";
        return "score-red";
    }

    function createListItems(parent, items) {
        items.forEach(function (text) {
            var li = document.createElement("li");
            li.textContent = text;
            parent.appendChild(li);
        });
    }

    function createCard(product) {
        var clone = template.content.cloneNode(true);
        var card = clone.querySelector(".product-card");

        card.classList.add(verdictClass(product.verdict));
        card.classList.add(scoreClass(product.trust_score));

        card.querySelector(".product-name").textContent = product.product_name;
        card.querySelector(".trust-score").textContent = product.trust_score;
        card.querySelector(".category-tag").textContent = product.category;
        card.querySelector(".verdict-tag").textContent = product.verdict;

        // Verdict summary
        var summary = card.querySelector(".verdict-summary");
        if (product.verdict_summary) {
            summary.textContent = product.verdict_summary;
        } else {
            summary.style.display = "none";
        }

        // Red flags
        var flagsList = card.querySelector(".red-flags-list");
        if (product.red_flags.length) {
            createListItems(flagsList, product.red_flags);
        } else {
            card.querySelector(".red-flags-section").style.display = "none";
        }

        // Claims
        var claimsList = card.querySelector(".claims-list");
        if (product.claims_extracted.length) {
            createListItems(claimsList, product.claims_extracted);
        } else {
            card.querySelector(".claims-section").style.display = "none";
        }

        // Evidence
        var evidenceText = card.querySelector(".evidence-text");
        if (product.evidence_check) {
            evidenceText.textContent = product.evidence_check;
        } else {
            card.querySelector(".evidence-section").style.display = "none";
        }

        // Sources
        var sourcesList = card.querySelector(".sources-list");
        if (product.sources.length) {
            createListItems(sourcesList, product.sources);
        } else {
            card.querySelector(".sources-section").style.display = "none";
        }

        // Badges
        if (product.ftc_complaint_ready) {
            card.querySelector(".badge-ftc").classList.add("visible");
        }
        if (product.fda_disclaimer_present) {
            card.querySelector(".badge-fda").classList.add("visible");
        }

        // Expand/collapse
        var expandBtn = card.querySelector(".expand-btn");
        expandBtn.addEventListener("click", function () {
            card.classList.toggle("expanded");
            expandBtn.textContent = card.classList.contains("expanded") ? "Collapse" : "Details";
        });

        return clone;
    }

    function render() {
        var filtered = filterProducts();

        // Clear grid using DOM methods
        while (grid.firstChild) {
            grid.removeChild(grid.firstChild);
        }

        resultsCount.textContent = "Showing " + filtered.length + " of " + allProducts.length + " products";

        if (filtered.length === 0) {
            var noResults = document.createElement("div");
            noResults.className = "no-results";
            var p = document.createElement("p");
            p.textContent = "No products match your search.";
            noResults.appendChild(p);
            grid.appendChild(noResults);
            return;
        }

        var fragment = document.createDocumentFragment();
        filtered.forEach(function (p) { fragment.appendChild(createCard(p)); });
        grid.appendChild(fragment);
    }
})();
