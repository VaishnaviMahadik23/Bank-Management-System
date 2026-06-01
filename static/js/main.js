document.addEventListener("DOMContentLoaded", function () {
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach(function (el) {
    setTimeout(function () {
      el.style.opacity = "0";
      el.style.transition = "opacity 0.4s";
      setTimeout(function () {
        el.remove();
      }, 400);
    }, 5000);
  });

  const amountInputs = document.querySelectorAll('input[type="number"][name="amount"]');
  amountInputs.forEach(function (input) {
    input.addEventListener("blur", function () {
      const val = parseFloat(this.value);
      if (!isNaN(val) && val < 0) {
        this.value = "";
      }
    });
  });
});
