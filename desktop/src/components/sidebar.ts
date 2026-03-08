/** Sidebar component — navigation between views. */

type View = "chat" | "agents" | "rag";

interface NavItem {
  id: View;
  label: string;
  icon: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: "chat", label: "Chat", icon: "💬" },
  { id: "agents", label: "Agents", icon: "🤖" },
  { id: "rag", label: "Knowledge", icon: "📚" },
];

let activeView: View = "chat";
let navContainer: HTMLElement | null = null;

export function renderSidebar(el: HTMLElement) {
  el.innerHTML = `
    <div class="sidebar__logo">VersaAI</div>
    <ul class="sidebar__nav" id="sidebar-nav"></ul>
  `;
  navContainer = el.querySelector("#sidebar-nav")!;
  renderNavItems();
}

function renderNavItems() {
  if (!navContainer) return;

  navContainer.innerHTML = NAV_ITEMS.map(
    (item) => `
    <li class="sidebar__item ${item.id === activeView ? "sidebar__item--active" : ""}"
        data-view="${item.id}">
      <span class="sidebar__icon">${item.icon}</span>
      <span>${item.label}</span>
    </li>
  `,
  ).join("");

  navContainer.querySelectorAll(".sidebar__item").forEach((li) => {
    li.addEventListener("click", () => {
      const view = (li as HTMLElement).dataset.view as View;
      const nav =
        (window as unknown as Record<string, unknown>).__navigateTo as (
          v: View,
        ) => void;
      nav(view);
    });
  });
}

export function setActiveView(view: View) {
  activeView = view;
  renderNavItems();
}
