document.addEventListener('DOMContentLoaded', function() {
    const languageSelect = document.querySelector('select[name="language"]');
    
    if (languageSelect) {
        languageSelect.addEventListener('change', function() {
            const currentPath = window.location.pathname;
            const selectedLanguage = this.value;
            
            // Разбираем текущий URL
            const pathParts = currentPath.split('/').filter(part => part !== '');
            
            // Если это страница товара: /язык/id/slug/
            if (pathParts.length === 3 && !isNaN(pathParts[1])) {
                const productId = pathParts[1];
                const currentSlug = pathParts[2];
                
                // Нужно получить slug на новом языке
                // Пока перенаправляем на главную, но можно улучшить
                window.location.href = '/' + selectedLanguage + '/';
                
            } 
            // Если это страница категории: /язык/category-slug/
            else if (pathParts.length === 2) {
                const categorySlug = pathParts[1];
                window.location.href = '/' + selectedLanguage + '/' + categorySlug + '/';
            }
            // Если это главная страница: /язык/
            else if (pathParts.length === 1) {
                window.location.href = '/' + selectedLanguage + '/';
            }
            // Для других страниц - на главную
            else {
                window.location.href = '/' + selectedLanguage + '/';
            }
        });
    }
});