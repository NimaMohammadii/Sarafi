// لیست ارزها و قیمت فرضی
const currencies = [
    { name: "بیت‌کوین", code: "BTC", price: 3500000000 },
    { name: "اتریوم", code: "ETH", price: 120000000 },
    { name: "تتر", code: "USDT", price: 60000 }
];

// نمایش لیست ارزها
const currencyTable = document.getElementById("currency-table");
currencies.forEach(cur => {
    const row = document.createElement("tr");
    row.innerHTML = `<td>${cur.name} (${cur.code})</td><td>${cur.price.toLocaleString()} </td>`;
    currencyTable.appendChild(row);
});

// ثبت تراکنش و نمایش
const tradeForm = document.getElementById("trade-form");
const transactionsList = document.getElementById("transactions-list");

tradeForm.addEventListener("submit", function(e) {
    e.preventDefault();
    const currency = tradeForm.currency.value;
    const type = tradeForm.type.value;
    const amount = parseFloat(tradeForm.amount.value);
    const currencyObj = currencies.find(c => c.code === currency);
    const price = currencyObj.price * amount;
    const text = `${type === "buy" ? "خرید" : "فروش"} ${amount} ${currencyObj.name} به مبلغ ${price.toLocaleString()} تومان`;
    const li = document.createElement("li");
    li.textContent = text;
    transactionsList.insertBefore(li, transactionsList.firstChild);
    tradeForm.reset();
});