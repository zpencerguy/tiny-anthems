(() => {
  const renderGenerationProgress = (form) => {
    const panel = form.closest(".action-panel");
    if (!panel) return;
    const progress = document.createElement("div");
    progress.innerHTML = `
      <div class="generation-progress" role="status" aria-live="polite">
        <p class="eyebrow">Generating</p>
        <h2>Your tiny anthem is in the mix.</h2>
        <p>Writing the hook, recording the vibe, and mixing it down. Keep this tab open.</p>
        <div class="progress-bars" aria-hidden="true"><span></span><span></span><span></span></div>
      </div>
    `;
    form.before(progress.firstElementChild);
    form.hidden = true;
  };

  const lockForm = (form) => {
    form.dataset.locked = "true";
    const loadingText = form.dataset.loadingText;
    form.querySelectorAll("button[type='submit']").forEach((button) => {
      button.disabled = true;
      button.setAttribute("aria-disabled", "true");
      if (loadingText) button.textContent = loadingText;
    });
  };

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.hasAttribute("data-submit-lock")) return;
    if (form.dataset.locked === "true") {
      event.preventDefault();
      return;
    }

    lockForm(form);
    if (form.hasAttribute("data-progress-on-submit")) {
      renderGenerationProgress(form);
    }
  });
})();
