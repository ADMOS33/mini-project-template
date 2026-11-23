// Toasts : toute erreur visible passe par ici (jamais de alert(), et la
// barre de statut n'affiche jamais d'erreur brute — règle front-end).

export function toast(message, kind = "error") {
  const box = document.getElementById("toasts");
  const el = document.createElement("div");
  el.className = "toast" + (kind === "info" ? " info" : "");
  el.textContent = message;
  box.appendChild(el);
  setTimeout(() => {
    el.style.transition = "opacity var(--tr)";
    el.style.opacity = "0";
    setTimeout(() => el.remove(), 200);
  }, 4000);
}

// Les erreurs API passent par un toast ; la barre de statut garde son texte.
export function reportError(prefix, err) {
  console.error(prefix, err);
  const msg = err && err.message ? err.message : String(err);
  toast(`${prefix} : ${msg}`);
}

// Toute erreur non interceptée (synchrone ou promesse) -> toast + console.
window.addEventListener("error", (e) => {
  console.error(e.error || e.message);
  toast("Erreur inattendue : " + (e.message || "inconnue"));
});
window.addEventListener("unhandledrejection", (e) => {
  console.error(e.reason);
  const msg = e.reason && e.reason.message ? e.reason.message : String(e.reason || "inconnue");
  toast("Erreur inattendue : " + msg);
});
