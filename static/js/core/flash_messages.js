document.addEventListener("DOMContentLoaded", () => {
  const data = document.getElementById("flashMessagesData");
  if (!data) return;

  const titles = {
    success: "成功",
    danger: "錯誤",
    warning: "提醒",
  };

  JSON.parse(data.textContent || "[]").forEach(([category, message]) => {
    Swal.fire({
      icon: category === "danger" ? "error" : (category || "info"),
      title: titles[category] || "通知",
      text: message,
      confirmButtonColor: "#2563eb",
    });
  });
});
