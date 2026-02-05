document.addEventListener("DOMContentLoaded", () => {
    const chips = document.querySelectorAll(".chip[data-filter]");
    const items = document.querySelectorAll(".newsletter-item");

    function getActiveValues(filterType) {
        const values = new Set();
        chips.forEach((chip) => {
            if (chip.dataset.filter === filterType && chip.classList.contains("active")) {
                values.add(chip.dataset.value);
            }
        });
        return values;
    }

    function applyFilters() {
        const activeSubs = getActiveValues("subreddit");
        const activeTools = getActiveValues("tool");
        const hasSubFilters = activeSubs.size > 0;
        const hasToolFilters = activeTools.size > 0;

        items.forEach((item) => {
            const sub = item.dataset.subreddit;
            const tools = (item.dataset.tools || "").split(",").filter(Boolean);

            let showBySub = !hasSubFilters || activeSubs.has(sub);
            let showByTool = !hasToolFilters || tools.some((t) => activeTools.has(t));

            if (showBySub && showByTool) {
                item.classList.remove("hidden");
            } else {
                item.classList.add("hidden");
            }
        });

        // Hide empty sections
        document.querySelectorAll(".newsletter-section").forEach((section) => {
            const visibleItems = section.querySelectorAll(".newsletter-item:not(.hidden)");
            section.style.display = visibleItems.length === 0 ? "none" : "";
        });
    }

    chips.forEach((chip) => {
        chip.addEventListener("click", () => {
            chip.classList.toggle("active");
            applyFilters();
        });
    });
});
