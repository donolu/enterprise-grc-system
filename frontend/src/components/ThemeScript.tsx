// Critical theme script that runs immediately to prevent flashing
export const ThemeScript = () => {
  const themeScript = `
    (function() {
      try {
        var savedTheme = localStorage.getItem('theme-mode');
        var html = document.documentElement;
        var body = document.body;

        // Detect system preference as fallback
        var systemPrefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        var shouldBeDark = savedTheme === 'dark' || (!savedTheme && systemPrefersDark);

        // Remove any existing theme classes
        html.classList.remove('light-mode', 'dark-mode');

        // Apply theme immediately
        if (shouldBeDark) {
          html.classList.add('dark-mode');
        } else {
          html.classList.add('light-mode');
        }

        // Mark as theme loaded to remove opacity
        html.classList.add('theme-loaded');

        // Add hydrated class for transitions
        setTimeout(function() {
          if (body) body.classList.add('hydrated');
        }, 50);

      } catch (e) {
        // Fallback - assume light mode and show page
        var html = document.documentElement || document.getElementsByTagName('html')[0];
        html.classList.add('light-mode', 'theme-loaded');
        setTimeout(function() {
          var body = document.body;
          if (body) body.classList.add('hydrated');
        }, 50);
      }
    })();
  `;

  return (
    <script
      dangerouslySetInnerHTML={{ __html: themeScript }}
      suppressHydrationWarning
    />
  );
};

export default ThemeScript;