// Track mouse position for radial glow effects
document.addEventListener('mousemove', (e) => {
  const cards = document.querySelectorAll('.card-legendary');
  cards.forEach(card => {
    const rect = card.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    (card as HTMLElement).style.setProperty('--mouse-x', `${x}%`);
    (card as HTMLElement).style.setProperty('--mouse-y', `${y}%`);
  });
});
