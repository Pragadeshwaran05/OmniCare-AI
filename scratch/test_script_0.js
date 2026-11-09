
        (function() {
            try {
                var theme = localStorage.getItem('omnicare_theme') || 'light';
                var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
                if (theme === 'dark' || (theme === 'system' && prefersDark)) {
                    document.documentElement.setAttribute('data-theme', 'dark');
                    document.documentElement.classList.add('theme-dark');
                } else {
                    document.documentElement.setAttribute('data-theme', 'light');
                    document.documentElement.classList.remove('theme-dark');
                }
                var sidebar = localStorage.getItem('omnicare_sidebar') || 'expanded';
                if (sidebar === 'compact' && window.innerWidth > 700) {
                    document.documentElement.classList.add('sidebar-compact');
                }
            } catch(e) {}
        })();
    