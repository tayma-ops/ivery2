'use strict';
(() => {
  let session = null,
    activeSlot = null,
    busy = false,
    submissionToken = crypto.randomUUID();
  const token = () => document.cookie.split('; ').find(x => x.startsWith('csrftoken='))?.split('=')[1] || '';
  const fields = document.querySelectorAll('.mwa-field select'),
    date = document.querySelector('.mwa-field input[type=date]');
  fields[0].id = 'specialty';
  fields[1].id = 'city';
  date.id = 'appointment-date';
  document.querySelectorAll('.mwa-field label').forEach((label, index) => label.htmlFor = ['specialty', 'city', 'appointment-date'][index]);
  const today = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Riyadh',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(new Date());
  date.min = today;
  date.value = today;
  const results = document.createElement('section');
  results.id = 'appointment-results';
  results.className = 'mwa-container';
  results.setAttribute('aria-live', 'polite');
  document.getElementById('booking').after(results);
  const dialog = document.createElement('dialog');
  dialog.id = 'appointment-dialog';
  dialog.innerHTML = '<form id="appointment-form"><h2>بيانات الحجز</h2><p id="appointment-summary"></p><label>اسم المراجع<input id="patient-name" required maxlength="100" autocomplete="name"></label><label>رقم الجوال<input id="patient-phone" required maxlength="20" autocomplete="tel" inputmode="tel"></label><p id="appointment-error" role="alert"></p><button type="submit">تأكيد طلب الموعد</button><button type="button" id="close-appointment">إغلاق</button></form>';
  document.body.append(dialog);
  document.getElementById('close-appointment').onclick = () => dialog.close();
  const style = document.createElement('style');
  style.textContent = '#appointment-results{padding:35px 20px}.appointment-result{margin:18px 0;padding:20px;border:1px solid #d8e8ec;border-radius:18px;background:#fff}.appointment-times{display:flex;gap:8px;flex-wrap:wrap}.appointment-times button,#appointment-form button{padding:10px 18px;border:0;border-radius:9px;background:#15758c;color:white;cursor:pointer}#appointment-dialog{border:0;border-radius:18px;max-width:480px;width:calc(100% - 32px);padding:25px}#appointment-dialog::backdrop{background:#0f293b88}#appointment-form label{display:block;margin:12px 0}#appointment-form input{display:block;width:100%;padding:12px;border:1px solid #bdd4dc;border-radius:8px;font:inherit}#appointment-error{color:#a02929}';
  document.head.append(style);
  document.getElementById('mwaSearchBtn').addEventListener('click', async event => {
    event.preventDefault();
    event.stopImmediatePropagation();
    if (busy) return;
    if (!session) {
      results.textContent = 'شغّل المشروع عبر python run_demo.py لعرض المواعيد وحفظها.';
      return;
    }
    if (fields[0].selectedIndex === 0 || fields[1].selectedIndex === 0 || !date.value) {
      results.textContent = 'اختر التخصص والمدينة والتاريخ.';
      return;
    }
    busy = true;
    results.textContent = 'جارٍ تحميل المواعيد…';
    try {
      const response = await fetch('/api/resources/?' + new URLSearchParams({
        specialty: fields[0].value.trim(),
        city: fields[1].value.trim()
      }));
      const data = await response.json();
      results.replaceChildren();
      for (const resource of data.resources) {
        const availability = await fetch('/api/availability/?' + new URLSearchParams({
          resource: resource.id,
          service: resource.service,
          date: date.value
        }));
        const slots = await availability.json();
        if (!availability.ok) throw Error(slots.error);
        const card = document.createElement('article');
        card.className = 'appointment-result';
        const title = document.createElement('h3');
        title.textContent = resource.name;
        const note = document.createElement('p');
        note.textContent = 'مقدم خدمة توضيحي لمعرض الأعمال — لا يمثل عيادة فعلية.';
        const times = document.createElement('div');
        times.className = 'appointment-times';
        for (const slot of slots.slots.filter(x => x.available)) {
          const button = document.createElement('button');
          button.type = 'button';
          button.textContent = slot.time;
          button.onclick = () => {
            if (!session.authenticated) {
              location.href = '/accounts/login/?next=/';
              return;
            }
            activeSlot = {
              resource: resource.id,
              service: resource.service,
              date: date.value,
              time: slot.time
            };
            document.getElementById('appointment-summary').textContent = resource.name + ' — ' + date.value + ' — ' + slot.time + ' (توقيت السعودية)';
            document.getElementById('appointment-error').textContent = '';
            dialog.showModal();
          };
          times.append(button);
        }
        if (!times.children.length) times.textContent = 'لا توجد مواعيد متاحة في هذا اليوم.';
        card.append(title, note, times);
        results.append(card);
      }
      if (!data.resources.length) results.textContent = 'لا يوجد مقدم خدمة مطابق حاليًا.';
      results.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    } catch (error) {
      results.textContent = error.message || 'تعذر تحميل المواعيد.';
    } finally {
      busy = false;
    }
  }, true);
  document.getElementById('appointment-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (!activeSlot) return;
    const button = event.currentTarget.querySelector('[type=submit]');
    button.disabled = true;
    try {
      const response = await fetch('/api/bookings/create/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': token()
        },
        body: JSON.stringify({
          ...activeSlot,
          token: submissionToken,
          customer: document.getElementById('patient-name').value,
          phone: document.getElementById('patient-phone').value
        })
      });
      const result = await response.json();
      if (!response.ok) throw Error(result.error || 'تحقق من البيانات.');
      submissionToken = crypto.randomUUID();
      location.href = '/bookings/';
    } catch (error) {
      document.getElementById('appointment-error').textContent = error.message;
      button.disabled = false;
    }
  });
  (async () => {
    try {
      const response = await fetch('/api/session/');
      if (!response.ok) return;
      session = await response.json();
      const link = document.createElement('a');
      link.href = '/bookings/';
      link.textContent = session.authenticated ? 'حجوزاتي وحسابي' : 'تسجيل الدخول وإنشاء حساب';
      link.style.cssText = 'display:block;padding:12px;text-align:center;background:#ecf9fc;color:#125c6a';
      document.body.prepend(link);
    } catch {}
  })();
})();
