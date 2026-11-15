(() => {
    const menu = document.querySelector(".category-menu");
    const toggle = document.getElementById("categoryToggle");
    const panel = document.getElementById("categoryPanel");

    if (!menu || !toggle || !panel) return;

    const backdrop = document.createElement("button");
    backdrop.className = "category-backdrop";
    backdrop.type = "button";
    backdrop.tabIndex = -1;
    backdrop.setAttribute("aria-label", "Close category menu");
    backdrop.hidden = true;
    document.body.insertBefore(backdrop, document.body.firstChild);

    const links = () => Array.from(panel.querySelectorAll("a[href]"));
    const isOpen = () => toggle.getAttribute("aria-expanded") === "true";

    function setOpen(open, focusTarget) {
        toggle.setAttribute("aria-expanded", String(open));
        panel.hidden = !open;
        backdrop.hidden = !open;

        if (open && focusTarget === "first") {
            links()[0]?.focus();
        } else if (open && focusTarget === "last") {
            links().at(-1)?.focus();
        } else if (!open && focusTarget === "toggle") {
            toggle.focus();
        }
    }

    toggle.addEventListener("click", () => setOpen(!isOpen()));

    toggle.addEventListener("keydown", event => {
        if (event.key === "ArrowDown") {
            event.preventDefault();
            setOpen(true, "first");
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            setOpen(true, "last");
        } else if (event.key === "Escape" && isOpen()) {
            event.preventDefault();
            setOpen(false, "toggle");
        }
    });

    panel.addEventListener("keydown", event => {
        if (event.key === "Escape") {
            event.preventDefault();
            setOpen(false, "toggle");
            return;
        }

        const menuLinks = links();
        const currentIndex = menuLinks.indexOf(document.activeElement);
        if (currentIndex === -1 || !["ArrowDown", "ArrowUp"].includes(event.key)) return;

        event.preventDefault();
        const direction = event.key === "ArrowDown" ? 1 : -1;
        const nextIndex = (currentIndex + direction + menuLinks.length) % menuLinks.length;
        menuLinks[nextIndex].focus();
    });

    backdrop.addEventListener("click", () => setOpen(false));
    document.addEventListener("pointerdown", event => {
        if (isOpen() && !menu.contains(event.target)) setOpen(false);
    });

    menu.addEventListener("focusout", () => {
        window.setTimeout(() => {
            if (isOpen() && !menu.contains(document.activeElement)) setOpen(false);
        }, 0);
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape" && isOpen()) {
            event.preventDefault();
            setOpen(false, "toggle");
        }
    });
})();
