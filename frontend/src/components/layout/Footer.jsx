export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="h-12 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 flex items-center justify-center">
      <p className="text-sm text-gray-600 dark:text-gray-400">
        © {currentYear} Elite Trading System. All rights reserved.
      </p>
    </footer>
  );
}

