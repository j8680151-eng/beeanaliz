// BeeAnaliz — Pure Vanilla JS Client (No Node.js, 100% Python + JSON)

let currentStoreId = 'baraka_market';
let storesList = [];
let storeProducts = [];
let storeSuppliers = [];
let storeNasiya = [];
let storeExpenses = [];
let storeOrders = [];

let posCart = [];
let heldCarts = [];
let activePaymentType = 'Naqd pul';
let activeBarcodeForPrint = { name: '', barcode: '' };
let activeDebtPaymentTarget = { type: '', id: '' };

// Format money in uz-UZ so'm
function formatMoney(amount) {
  if (amount === undefined || amount === null) return "0 so'm";
  return new Intl.NumberFormat('uz-UZ').format(Math.round(amount)) + " so'm";
}

// Initialize on page load
window.addEventListener('DOMContentLoaded', async () => {
  if (window.lucide) window.lucide.createIcons();
  await loadStoresList();
  await loadStoreData(currentStoreId);
  switchTab('pos');
});

// Refresh Lucide icons
function refreshIcons() {
  if (window.lucide) {
    setTimeout(() => window.lucide.createIcons(), 50);
  }
}

// ----------------- TAB NAVIGATION ----------------- //
function switchTab(tabId) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.classList.remove('bg-slate-900', 'text-white', 'bg-amber-500', 'text-slate-950');
    btn.classList.add('text-slate-600');
  });

  const activeContent = document.getElementById(`tab-${tabId}`);
  if (activeContent) activeContent.classList.remove('hidden');

  const activeNav = document.getElementById(`nav-${tabId}`);
  if (activeNav) {
    activeNav.classList.remove('text-slate-600');
    if (tabId === 'pos') {
      activeNav.classList.add('bg-amber-500', 'text-slate-950');
    } else {
      activeNav.classList.add('bg-slate-900', 'text-white');
    }
  }

  if (tabId === 'pos') {
    setTimeout(() => {
      const scanInput = document.getElementById('posScanInput');
      if (scanInput) scanInput.focus();
    }, 100);
  }

  refreshIcons();
}

// ----------------- STORES MANAGEMENT (JSON) ----------------- //
async function loadStoresList() {
  try {
    const res = await fetch('/api/stores');
    storesList = await res.json();
    const select = document.getElementById('storeSelect');
    select.innerHTML = '';
    
    storesList.forEach(store => {
      const opt = document.createElement('option');
      opt.value = store.id;
      opt.textContent = `${store.name} (${store.owner_name || 'Egasi'})`;
      if (store.id === currentStoreId) opt.selected = true;
      select.appendChild(opt);
    });

    if (storesList.length > 0 && !storesList.some(s => s.id === currentStoreId)) {
      currentStoreId = storesList[0].id;
      select.value = currentStoreId;
    }
  } catch (err) {
    console.error("Do'konlarni yuklashda xatolik:", err);
  }
}

async function onStoreChange(newStoreId) {
  currentStoreId = newStoreId;
  posCart = [];
  renderPosCart();
  await loadStoreData(currentStoreId);
}

async function loadStoreData(storeId) {
  try {
    const [pRes, sRes, nRes, eRes, oRes] = await Promise.all([
      fetch(`/api/stores/${storeId}/products`),
      fetch(`/api/stores/${storeId}/suppliers`),
      fetch(`/api/stores/${storeId}/nasiya`),
      fetch(`/api/stores/${storeId}/expenses`),
      fetch(`/api/stores/${storeId}/orders`)
    ]);

    storeProducts = await pRes.json();
    storeSuppliers = await sRes.json();
    storeNasiya = await nRes.json();
    storeExpenses = await eRes.json();
    storeOrders = await oRes.json();

    renderPosQuickGrid();
    renderInventoryTable();
    renderSuppliersTable();
    renderNasiyaTable();
    renderExpensesTable();
    renderAnalytics();
    populateIntakeSuppliers();
  } catch (err) {
    console.error("Do'kon ma'lumotlarini yuklashda xatolik:", err);
  }
}

function openRegisterStoreModal() {
  document.getElementById('registerStoreModal').classList.remove('hidden');
}

function closeRegisterStoreModal() {
  document.getElementById('registerStoreModal').classList.add('hidden');
}

async function handleRegisterStore(e) {
  e.preventDefault();
  const name = document.getElementById('regStoreName').value;
  const owner_name = document.getElementById('regOwnerName').value;
  const phone = document.getElementById('regPhone').value;
  const address = document.getElementById('regAddress').value;

  try {
    const res = await fetch('/api/stores/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, owner_name, phone, address })
    });
    const newStore = await res.json();
    closeRegisterStoreModal();
    alert(`"${newStore.name}" do'koni uchun shaxsiy JSON bazasi yaratildi!`);
    await loadStoresList();
    await onStoreChange(newStore.id);
  } catch (err) {
    alert("Do'kon yaratishda xatolik yuz berdi");
  }
}

// Audio beep for scanner
let appAudioCtx = null;
function playAppBeep(success = true) {
  try {
    if (!appAudioCtx) appAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (appAudioCtx.state === 'suspended') appAudioCtx.resume();
    const osc = appAudioCtx.createOscillator();
    const gain = appAudioCtx.createGain();
    osc.connect(gain);
    gain.connect(appAudioCtx.destination);
    
    if (success) {
      osc.frequency.setValueAtTime(1100, appAudioCtx.currentTime);
      gain.gain.setValueAtTime(0.18, appAudioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, appAudioCtx.currentTime + 0.09);
      osc.start();
      osc.stop(appAudioCtx.currentTime + 0.09);
    } else {
      osc.frequency.setValueAtTime(320, appAudioCtx.currentTime);
      gain.gain.setValueAtTime(0.25, appAudioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, appAudioCtx.currentTime + 0.18);
      osc.start();
      osc.stop(appAudioCtx.currentTime + 0.18);
    }
  } catch (e) {}
}

function showAppToast(message, isSuccess = true) {
  let toast = document.getElementById('appScanToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'appScanToast';
    document.body.appendChild(toast);
  }
  toast.className = `fixed bottom-6 right-6 z-50 px-4 py-3 rounded-2xl shadow-xl font-bold text-xs flex items-center space-x-2 transition-all transform duration-300 ${isSuccess ? 'bg-emerald-600 text-white shadow-emerald-500/20' : 'bg-rose-600 text-white shadow-rose-500/20'}`;
  toast.innerHTML = isSuccess 
    ? `<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg><span>${message}</span>`
    : `<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg><span>${message}</span>`;
  toast.style.opacity = '1';
  toast.style.transform = 'translateY(0)';
  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(20px)';
  }, 2200);
}

// Global Barcode Listener for app.js
let appBarcodeBuffer = '';
let appLastKeyTime = 0;
let appLastProcessedCode = '';
let appLastScanTime = 0;

window.addEventListener('keydown', (e) => {
  const activeEl = document.activeElement;
  if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.tagName === 'SELECT')) {
    return;
  }

  const now = Date.now();
  const diff = now - appLastKeyTime;
  appLastKeyTime = now;

  if (diff > 120) {
    appBarcodeBuffer = '';
  }

  if (e.key === 'Enter') {
    if (appBarcodeBuffer.length >= 3) {
      e.preventDefault();
      const code = appBarcodeBuffer.trim();
      appBarcodeBuffer = '';
      handlePosScan(code);
    }
  } else if (e.key.length === 1) {
    appBarcodeBuffer += e.key;
  }
});

// ----------------- SKANERLI KASSA (POS) ----------------- //
function handlePosScan(barcodeQuery) {
  const query = (barcodeQuery || '').replace(/[\r\n\t]/g, '').trim().toLowerCase();
  const input = document.getElementById('posScanInput');
  if (input) input.value = '';

  if (!query) return;

  // Dublikatdan himoya: 700ms ichida 2 marta qo'shmaslik
  const now = Date.now();
  if (query === appLastProcessedCode && (now - appLastScanTime) < 700) {
    return;
  }
  appLastProcessedCode = query;
  appLastScanTime = now;

  const product = storeProducts.find(p =>
    String(p.barcode).trim().toLowerCase() === query ||
    String(p.sku || '').trim().toLowerCase() === query ||
    p.name.toLowerCase().includes(query)
  );

  if (!product) {
    playAppBeep(false);
    showAppToast(`"${barcodeQuery}" shtrix-kodli tovar topilmadi!`, false);
    return;
  }

  if (product.stock <= 0) {
    playAppBeep(false);
    showAppToast(`"${product.name}" omborda tugagan (0 dona)!`, false);
    return;
  }

  playAppBeep(true);
  addToCart(product);
  showAppToast(`"${product.name}" savatga qo'shildi (+1 dona)`, true);
}

function addToCart(product) {
  const existing = posCart.find(i => i.id === product.id || i.barcode === product.barcode);
  if (existing) {
    if (existing.quantity >= product.stock) {
      alert(`Omborda bu mahsulotdan faqat ${product.stock} ta bor!`);
      return;
    }
    existing.quantity += 1;
  } else {
    posCart.unshift({
      id: product.id,
      name: product.name,
      barcode: product.barcode,
      sku: product.sku || '',
      price: product.sellingPrice,
      cost: product.costPrice || 0,
      stock: product.stock,
      unit: product.unit || 'dona',
      quantity: 1
    });
  }

  renderPosCart();
}

function updateCartQty(idx, delta) {
  if (!posCart[idx]) return;
  const item = posCart[idx];
  const newQty = item.quantity + delta;

  if (newQty <= 0) {
    posCart.splice(idx, 1);
  } else if (newQty > item.stock) {
    alert(`Omborda faqat ${item.stock} ta bor!`);
    return;
  } else {
    item.quantity = newQty;
  }

  renderPosCart();
}

function removeCartItem(idx) {
  posCart.splice(idx, 1);
  renderPosCart();
}

function clearCart() {
  if (posCart.length === 0) return;
  if (confirm("Savatni tozalashni xohlaysizmi?")) {
    posCart = [];
    renderPosCart();
  }
}

function holdCart() {
  if (posCart.length === 0) {
    alert("Savat bo'sh, saqlash uchun tovar qo'shing!");
    return;
  }
  const custName = prompt("Xaridor ismi yoki paket raqami (Otlojka):", "Xaridor");
  heldCarts.push({
    id: 'HOLD-' + Math.floor(100 + Math.random() * 900),
    time: new Date().toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' }),
    name: custName || 'Xaridor',
    items: [...posCart]
  });
  posCart = [];
  renderPosCart();
  renderHeldCarts();
}

function restoreHeldCart(holdIdx) {
  const held = heldCarts.splice(holdIdx, 1)[0];
  if (held) {
    posCart = held.items;
    renderPosCart();
    renderHeldCarts();
  }
}

function renderHeldCarts() {
  const box = document.getElementById('heldCartsBox');
  const list = document.getElementById('heldCartsList');
  const countBadge = document.getElementById('heldCartsCount');

  if (heldCarts.length === 0) {
    box.classList.add('hidden');
    return;
  }

  box.classList.remove('hidden');
  countBadge.textContent = heldCarts.length;
  list.innerHTML = heldCarts.map((h, idx) => {
    const total = h.items.reduce((s, i) => s + i.price * i.quantity, 0);
    return `
      <div class="flex items-center justify-between p-2 bg-slate-50 rounded-lg border border-slate-200">
        <div>
          <span class="font-bold text-slate-800">${h.name}</span>
          <span class="text-[10px] text-slate-400 block">${h.time} | ${formatMoney(total)}</span>
        </div>
        <button onclick="restoreHeldCart(${idx})" class="px-2.5 py-1 bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold rounded text-[10px]">
          Yuklash
        </button>
      </div>
    `;
  }).join('');
}

function renderPosCart() {
  const tbody = document.getElementById('posCartTableBody');
  const emptyNotice = document.getElementById('posEmptyCartNotice');
  const countBadge = document.getElementById('posCartCountBadge');
  const summaryCount = document.getElementById('posSummaryCount');
  const summarySubtotal = document.getElementById('posSummarySubtotal');
  const summaryTotal = document.getElementById('posSummaryTotal');

  if (posCart.length === 0) {
    tbody.innerHTML = '';
    emptyNotice.classList.remove('hidden');
    countBadge.textContent = '0 ta';
    summaryCount.textContent = '0 dona';
    summarySubtotal.textContent = "0 so'm";
    summaryTotal.textContent = "0 so'm";
    return;
  }

  emptyNotice.classList.add('hidden');
  const totalCount = posCart.reduce((s, i) => s + i.quantity, 0);
  const totalPrice = posCart.reduce((s, i) => s + i.price * i.quantity, 0);

  countBadge.textContent = `${posCart.length} xil`;
  summaryCount.textContent = `${totalCount} dona`;
  summarySubtotal.textContent = formatMoney(totalPrice);
  summaryTotal.textContent = formatMoney(totalPrice);

  tbody.innerHTML = posCart.map((item, idx) => `
    <tr class="hover:bg-slate-50 transition">
      <td class="py-2.5 px-4 text-slate-400 font-bold">${idx + 1}</td>
      <td class="py-2.5 px-4">
        <span class="font-bold text-slate-900 block leading-tight">${item.name}</span>
        <span class="text-[10px] text-slate-400">Omborda: ${item.stock} ${item.unit}</span>
      </td>
      <td class="py-2.5 px-4 font-mono font-bold text-slate-600">${item.barcode}</td>
      <td class="py-2.5 px-4 text-center">
        <div class="inline-flex items-center space-x-1.5 bg-slate-100 p-0.5 rounded-lg border border-slate-200">
          <button onclick="updateCartQty(${idx}, -1)" class="w-6 h-6 flex items-center justify-center font-black hover:bg-white rounded transition">-</button>
          <span class="font-bold font-mono px-1.5">${item.quantity}</span>
          <button onclick="updateCartQty(${idx}, 1)" class="w-6 h-6 flex items-center justify-center font-black hover:bg-white rounded transition">+</button>
        </div>
      </td>
      <td class="py-2.5 px-4 text-right font-mono font-bold text-slate-700">${formatMoney(item.price)}</td>
      <td class="py-2.5 px-4 text-right font-mono font-extrabold text-amber-600">${formatMoney(item.price * item.quantity)}</td>
      <td class="py-2.5 px-3 text-center">
        <button onclick="removeCartItem(${idx})" class="text-slate-300 hover:text-rose-600 transition">
          <i data-lucide="x" class="w-4 h-4"></i>
        </button>
      </td>
    </tr>
  `).join('');

  refreshIcons();
}

function renderPosQuickGrid() {
  const grid = document.getElementById('posQuickGrid');
  if (!grid) return;
  grid.innerHTML = storeProducts.slice(0, 8).map(p => `
    <div onclick='addToCart(${JSON.stringify(p)})' class="p-3 bg-slate-50 hover:bg-amber-50 border border-slate-200/80 hover:border-amber-300 rounded-xl cursor-pointer transition select-none flex flex-col justify-between">
      <span class="font-bold text-xs text-slate-900 leading-tight line-clamp-2">${p.name}</span>
      <div class="flex items-center justify-between mt-2 pt-1 border-t border-slate-200/50">
        <span class="font-mono font-black text-amber-600 text-xs">${formatMoney(p.sellingPrice)}</span>
        <span class="text-[10px] text-slate-400 font-bold">${p.stock} ta</span>
      </div>
    </div>
  `).join('');
}

// ----------------- CHECKOUT & CHEK (RECEIPT) ----------------- //
function openCheckoutModal(paymentType) {
  if (posCart.length === 0) {
    alert("Savat bo'sh! Xarid qilish uchun avval tovar qo'shing.");
    return;
  }
  activePaymentType = paymentType;
  const total = posCart.reduce((s, i) => s + i.price * i.quantity, 0);

  document.getElementById('checkoutModalTitle').textContent = `${paymentType.toUpperCase()} TO'LOV`;
  document.getElementById('checkoutModalTotal').textContent = formatMoney(total);

  const nasiyaFields = document.getElementById('nasiyaFields');
  if (paymentType === 'Nasiya') {
    nasiyaFields.classList.remove('hidden');
  } else {
    nasiyaFields.classList.add('hidden');
  }

  document.getElementById('checkoutModal').classList.remove('hidden');
}

function closeCheckoutModal() {
  document.getElementById('checkoutModal').classList.add('hidden');
}

async function confirmPosSale() {
  const payload = {
    paymentType: activePaymentType,
    cashGiven: posCart.reduce((s, i) => s + i.price * i.quantity, 0),
    nasiyaCustomer: activePaymentType === 'Nasiya' ? document.getElementById('nasiyaCustName').value.trim() : null,
    nasiyaPhone: activePaymentType === 'Nasiya' ? document.getElementById('nasiyaCustPhone').value.trim() : null,
    nasiyaDueDate: activePaymentType === 'Nasiya' ? document.getElementById('nasiyaCustDueDate').value : null,
    items: posCart
  };

  try {
    const res = await fetch(`/api/stores/${currentStoreId}/pos/checkout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error("Savdo amalga oshmadi");
    const orderRecord = await res.json();
    closeCheckoutModal();

    // Reload products & orders
    await loadStoreData(currentStoreId);
    posCart = [];
    renderPosCart();

    // Show thermal receipt modal
    openReceiptModal(orderRecord);
  } catch (err) {
    alert("Savdoni rasmiylashtirishda xatolik yuz berdi");
  }
}

function openReceiptModal(order) {
  const currentStore = storesList.find(s => s.id === currentStoreId);
  document.getElementById('receiptStoreName').textContent = currentStore ? currentStore.name : 'Baraka Savdo Markazi';
  document.getElementById('receiptDate').textContent = order.date;
  document.getElementById('receiptOrderId').textContent = order.id;
  document.getElementById('receiptCustomer').textContent = order.customerName || 'Xaridor';
  document.getElementById('receiptTotalAmount').textContent = formatMoney(order.totalAmount);
  document.getElementById('receiptPaymentMethod').textContent = order.paymentMethod;

  const itemsContainer = document.getElementById('receiptItemsList');
  itemsContainer.innerHTML = order.items.map((it, idx) => `
    <div class="border-b border-slate-100 pb-1.5 last:border-0 last:pb-0">
      <div class="flex justify-between font-bold text-slate-900 text-[11px] leading-tight">
        <span>${idx + 1}. ${it.name}</span>
        <span>${formatMoney(it.price * it.quantity)}</span>
      </div>
      <div class="flex items-center justify-between text-[10px] text-slate-500 mt-0.5 font-mono">
        <span>Shtrix: <strong>${it.barcode}</strong></span>
        <span>${it.quantity} ${it.unit || 'dona'} &times; ${formatMoney(it.price)}</span>
      </div>
    </div>
  `).join('');

  document.getElementById('receiptModal').classList.remove('hidden');
}

function closeReceiptModal() {
  document.getElementById('receiptModal').classList.add('hidden');
}

function triggerReceiptPrint() {
  const orderId = document.getElementById('receiptOrderId').textContent;
  window.open(`/api/receipt-print?store_id=${currentStoreId}&order_id=${orderId}`, '_blank', 'width=400,height=600');
}

// ----------------- TOVAR KIRIMI (INTAKE) ----------------- //
function generateRandomBarcode() {
  const code = '4780' + Math.floor(10000 + Math.random() * 90000);
  document.getElementById('intakeBarcode').value = code;
}

function lookupBarcodeForIntake(barcode) {
  const clean = barcode.trim();
  const existing = storeProducts.find(p => String(p.barcode) === clean);
  if (existing) {
    document.getElementById('intakeName').value = existing.name;
    document.getElementById('intakeCategory').value = existing.category || 'Umumiy';
    document.getElementById('intakeUnit').value = existing.unit || 'dona';
    document.getElementById('intakeCostPrice').value = existing.costPrice;
    document.getElementById('intakeSellingPrice').value = existing.sellingPrice;
  }
}

function populateIntakeSuppliers() {
  const select = document.getElementById('intakeSupplierSelect');
  if (!select) return;
  select.innerHTML = '<option value="">-- Ta\'minotchisiz --</option>';
  storeSuppliers.forEach(sup => {
    const opt = document.createElement('option');
    opt.value = sup.id;
    opt.textContent = `${sup.name} (Qarz: ${formatMoney(sup.debt || 0)})`;
    select.appendChild(opt);
  });
}

async function handleIntakeSubmit(e) {
  e.preventDefault();
  const payload = {
    barcode: document.getElementById('intakeBarcode').value.trim(),
    name: document.getElementById('intakeName').value.trim(),
    category: document.getElementById('intakeCategory').value.trim(),
    unit: document.getElementById('intakeUnit').value,
    quantity: parseFloat(document.getElementById('intakeQuantity').value),
    costPrice: parseFloat(document.getElementById('intakeCostPrice').value),
    sellingPrice: parseFloat(document.getElementById('intakeSellingPrice').value),
    supplierId: document.getElementById('intakeSupplierSelect').value || null
  };

  try {
    const res = await fetch(`/api/stores/${currentStoreId}/products/intake`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("Kirim muvaffaqiyatsiz");
    const updated = await res.json();
    alert(`"${updated.name}" muvaffaqiyatli omborga qabul qilindi va JSON faylga yozildi!`);
    
    // Clear & reload
    document.getElementById('intakeForm').reset();
    await loadStoreData(currentStoreId);
    switchTab('inventory');
  } catch (err) {
    alert("Omborga tovar qabul qilishda xatolik yuz berdi");
  }
}

// ----------------- TOVARLAR & SHTRIX-KOD CHOP ETISH ----------------- //
function renderInventoryTable(query = '') {
  const tbody = document.getElementById('inventoryTableBody');
  if (!tbody) return;

  const q = query.trim().toLowerCase();
  const filtered = storeProducts.filter(p =>
    p.name.toLowerCase().includes(q) || String(p.barcode).includes(q)
  );

  tbody.innerHTML = filtered.map(p => `
    <tr class="hover:bg-slate-50 transition">
      <td class="py-3 px-4 font-mono font-bold text-slate-700">${p.barcode}</td>
      <td class="py-3 px-4 font-bold text-slate-900">${p.name}</td>
      <td class="py-3 px-4 text-slate-500">${p.category || 'Umumiy'}</td>
      <td class="py-3 px-4 text-right font-mono text-slate-600">${formatMoney(p.costPrice)}</td>
      <td class="py-3 px-4 text-right font-mono font-bold text-amber-600">${formatMoney(p.sellingPrice)}</td>
      <td class="py-3 px-4 text-center font-bold ${p.stock <= 5 ? 'text-rose-600 bg-rose-50/50' : 'text-slate-800'}">
        ${p.stock} ${p.unit || 'dona'}
      </td>
      <td class="py-3 px-4 text-center">
        <button onclick='openBarcodePrintModal(${JSON.stringify(p.name)}, ${JSON.stringify(p.barcode)})' class="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-lg text-xs flex items-center space-x-1 mx-auto transition" title="Shtrix-kod chop etish">
          <i data-lucide="printer" class="w-3.5 h-3.5 text-amber-400"></i>
          <span>Shtrix-kod</span>
        </button>
      </td>
    </tr>
  `).join('');

  refreshIcons();
}

async function openBarcodePrintModal(name, barcode_num) {
  activeBarcodeForPrint = { name, barcode: barcode_num };
  document.getElementById('modalBarcodeProdName').textContent = name;
  document.getElementById('modalBarcodeProdNumber').textContent = barcode_num;

  try {
    const savedSize = localStorage.getItem('be_preferred_label_size') || '58x40';
    const sizeSelect = document.getElementById('indexBarcodeSizeSelect');
    if (sizeSelect) sizeSelect.value = savedSize;
    const copiesInput = document.getElementById('indexBarcodeCopiesInput');
    if (copiesInput) copiesInput.value = 1;
  } catch(e) {}

  const svgBox = document.getElementById('modalBarcodeSvgContainer');
  svgBox.innerHTML = '<span class="text-xs text-slate-400">Shtrix-kod yuklanmoqda...</span>';

  try {
    const res = await fetch(`/api/barcode-svg/${encodeURIComponent(barcode_num)}`);
    const svgContent = await res.text();
    svgBox.innerHTML = svgContent || `<div style="font-family: monospace; letter-spacing: 2px;">||||||||||||||||</div>`;
  } catch (err) {
    svgBox.innerHTML = `<div style="font-family: monospace; letter-spacing: 2px;">||||||||||||||||</div>`;
  }

  document.getElementById('barcodePrintModal').classList.remove('hidden');
  refreshIcons();
}

function closeBarcodePrintModal() {
  document.getElementById('barcodePrintModal').classList.add('hidden');
}

function triggerDirectBarcodePrint() {
  const { name, barcode } = activeBarcodeForPrint;
  const sizeSelect = document.getElementById('indexBarcodeSizeSelect');
  const copiesInput = document.getElementById('indexBarcodeCopiesInput');
  const size = sizeSelect ? sizeSelect.value : '58x40';
  const copies = copiesInput ? (parseInt(copiesInput.value) || 1) : 1;

  try {
    localStorage.setItem('be_preferred_label_size', size);
  } catch (e) {}

  const url = `/api/barcode-print?name=${encodeURIComponent(name)}&barcode_num=${encodeURIComponent(barcode)}&size=${encodeURIComponent(size)}&copies=${copies}&auto_print=1`;
  window.open(url, '_blank', 'width=520,height=600');
  closeBarcodePrintModal();
}

// ----------------- NASIYA DAFTARI ----------------- //
function renderNasiyaTable() {
  const tbody = document.getElementById('nasiyaTableBody');
  const badge = document.getElementById('totalNasiyaDebtBadge');
  if (!tbody) return;

  const totalDebt = storeNasiya.reduce((s, n) => s + (n.remainingDebt || 0), 0);
  badge.textContent = `Jami Nasiya: ${formatMoney(totalDebt)}`;

  tbody.innerHTML = storeNasiya.map(nas => `
    <tr class="hover:bg-slate-50 transition">
      <td class="py-3 px-4 font-bold text-slate-900">${nas.customerName}</td>
      <td class="py-3 px-4 font-mono text-slate-600">${nas.phone || '-'}</td>
      <td class="py-3 px-4 text-slate-500">${nas.date}</td>
      <td class="py-3 px-4 text-slate-700 font-bold">${nas.dueDate || 'Muddatsiz'}</td>
      <td class="py-3 px-4 text-right font-mono font-bold">${formatMoney(nas.totalAmount)}</td>
      <td class="py-3 px-4 text-right font-mono font-black text-rose-600">${formatMoney(nas.remainingDebt)}</td>
      <td class="py-3 px-4 text-center">
        <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${nas.remainingDebt === 0 ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">
          ${nas.status}
        </span>
      </td>
      <td class="py-3 px-4 text-center">
        ${nas.remainingDebt > 0 ? `
          <button onclick="openPayDebtModal('nasiya', '${nas.id}', '${nas.customerName}', ${nas.remainingDebt})" class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg text-xs transition">
            To'lash
          </button>
        ` : `<span class="text-emerald-600 font-bold text-xs">Yopilgan</span>`}
      </td>
    </tr>
  `).join('');
}

// ----------------- TA'MINOTCHILAR ----------------- //
function renderSuppliersTable() {
  const tbody = document.getElementById('suppliersTableBody');
  const badge = document.getElementById('totalSupplierDebtBadge');
  if (!tbody) return;

  const totalDebt = storeSuppliers.reduce((s, sup) => s + (sup.debt || 0), 0);
  badge.textContent = `Ta'minotchilarga Qarz: ${formatMoney(totalDebt)}`;

  tbody.innerHTML = storeSuppliers.map(sup => `
    <tr class="hover:bg-slate-50 transition">
      <td class="py-3 px-4 font-bold text-slate-900">${sup.name}</td>
      <td class="py-3 px-4 font-mono text-slate-600">${sup.phone || '-'}</td>
      <td class="py-3 px-4 text-right font-mono font-bold">${formatMoney(sup.totalDelivered)}</td>
      <td class="py-3 px-4 text-right font-mono text-emerald-600">${formatMoney(sup.paidAmount)}</td>
      <td class="py-3 px-4 text-right font-mono font-black text-amber-600">${formatMoney(sup.debt)}</td>
      <td class="py-3 px-4 text-center">
        ${sup.debt > 0 ? `
          <button onclick="openPayDebtModal('supplier', '${sup.id}', '${sup.name}', ${sup.debt})" class="px-2.5 py-1 bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold rounded-lg text-xs transition">
            Qarz to'lash
          </button>
        ` : `<span class="text-slate-400 text-xs">Qarz yo'q</span>`}
      </td>
    </tr>
  `).join('');
}

function openPayDebtModal(type, id, title, maxDebt) {
  activeDebtPaymentTarget = { type, id };
  document.getElementById('payDebtModalTitle').textContent = `${title} uchun qarz to'lovi (Qarz: ${formatMoney(maxDebt)})`;
  document.getElementById('payDebtAmount').value = maxDebt;
  document.getElementById('payDebtModal').classList.remove('hidden');
}

function closePayDebtModal() {
  document.getElementById('payDebtModal').classList.add('hidden');
}

async function handleDebtPaymentSubmit(e) {
  e.preventDefault();
  const amount = parseFloat(document.getElementById('payDebtAmount').value);
  const note = document.getElementById('payDebtNote').value;

  const { type, id } = activeDebtPaymentTarget;
  const endpoint = type === 'nasiya'
    ? `/api/stores/${currentStoreId}/nasiya/${id}/pay`
    : `/api/stores/${currentStoreId}/suppliers/${id}/pay`;

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount, note })
    });
    if (!res.ok) throw new Error("To'lov bajarilmadi");
    closePayDebtModal();
    alert("To'lov muvaffaqiyatli amalga oshirildi!");
    await loadStoreData(currentStoreId);
  } catch (err) {
    alert("To'lovni saqlashda xatolik yuz berdi");
  }
}

// ----------------- XARAJATLAR ----------------- //
function renderExpensesTable() {
  const tbody = document.getElementById('expensesTableBody');
  if (!tbody) return;

  tbody.innerHTML = storeExpenses.map(e => `
    <tr class="hover:bg-slate-50 transition">
      <td class="py-3 px-4 font-mono text-slate-500">${e.date}</td>
      <td class="py-3 px-4 font-bold text-slate-900">${e.title}</td>
      <td class="py-3 px-4"><span class="bg-slate-100 px-2 py-0.5 rounded text-[10px] font-bold text-slate-700">${e.category}</span></td>
      <td class="py-3 px-4 text-right font-mono font-black text-rose-600">${formatMoney(e.amount)}</td>
    </tr>
  `).join('');
}

async function handleExpenseSubmit(e) {
  e.preventDefault();
  const title = document.getElementById('expenseTitle').value.trim();
  const category = document.getElementById('expenseCategory').value;
  const amount = parseFloat(document.getElementById('expenseAmount').value);

  try {
    const res = await fetch(`/api/stores/${currentStoreId}/expenses`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, category, amount })
    });
    if (!res.ok) throw new Error("Xarajat saqlanmadi");
    document.getElementById('expenseTitle').value = '';
    document.getElementById('expenseAmount').value = '';
    await loadStoreData(currentStoreId);
  } catch (err) {
    alert("Xarajatni saqlashda xatolik yuz berdi");
  }
}

// ----------------- HISOBOT (ANALYTICS) ----------------- //
function renderAnalytics() {
  const totalRev = storeOrders.reduce((s, o) => s + (o.totalAmount || 0), 0);
  const totalProfit = storeOrders.reduce((s, o) => s + (o.profit || 0), 0);

  document.getElementById('statDailyRevenue').textContent = formatMoney(totalRev);
  document.getElementById('statDailyProfit').textContent = formatMoney(totalProfit);
  document.getElementById('statOrdersCount').textContent = `${storeOrders.length} ta`;

  const tbody = document.getElementById('ordersTableBody');
  if (!tbody) return;

  tbody.innerHTML = storeOrders.map(o => `
    <tr class="hover:bg-slate-50 transition">
      <td class="py-3 px-4 font-mono font-bold text-slate-900">${o.id}</td>
      <td class="py-3 px-4 font-mono text-slate-500">${o.date}</td>
      <td class="py-3 px-4 font-bold text-slate-700">${o.customerName || 'Xaridor'}</td>
      <td class="py-3 px-4 font-bold text-xs uppercase">${o.paymentMethod}</td>
      <td class="py-3 px-4 text-right font-mono font-black text-amber-600">${formatMoney(o.totalAmount)}</td>
      <td class="py-3 px-4 text-center">
        <button onclick='openReceiptModal(${JSON.stringify(o)})' class="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold rounded-lg text-xs transition">
          Ko'rish
        </button>
      </td>
    </tr>
  `).join('');
}
