document.querySelectorAll(".announcement-tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".announcement-tab").forEach((item) => {
      item.classList.toggle("is-active", item === button);
    });
    document.querySelectorAll(".announcement-pane").forEach((pane) => {
      pane.classList.toggle("d-none", pane.dataset.pane !== button.dataset.target);
    });
  });
});
