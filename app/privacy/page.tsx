import InteractiveFooter from '@/components/InteractiveFooter'

export const metadata = {
  title: 'Политика конфиденциальности | Premium Agency',
  description: 'Политика обработки персональных данных',
}

export default function PrivacyPage() {
  return (
    <>
      <main className="min-h-screen pt-32 px-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-6xl font-black mb-8">Политика конфиденциальности</h1>
          
          <div className="prose prose-invert prose-lg max-w-none">
            <p className="text-accent text-xl mb-8">
              Последнее обновление: {new Date().toLocaleDateString('ru-RU')}
            </p>

            <h2>1. Общие положения</h2>
            <p>
              Настоящая Политика конфиденциальности определяет порядок обработки и защиты персональных данных пользователей сайта.
            </p>

            <h2>2. Собираемые данные</h2>
            <p>Мы собираем следующую информацию:</p>
            <ul>
              <li>Имя и контактные данные</li>
              <li>Информация о компании</li>
              <li>Данные об использовании сайта</li>
              <li>Cookies и технические данные</li>
            </ul>

            <h2>3. Цели обработки данных</h2>
            <ul>
              <li>Обработка запросов и обращений</li>
              <li>Улучшение качества услуг</li>
              <li>Аналитика и статистика</li>
              <li>Маркетинговые коммуникации (с согласия)</li>
            </ul>

            <h2>4. Защита данных</h2>
            <p>
              Мы применяем современные технологии защиты данных: шифрование, безопасное хранение, ограниченный доступ.
            </p>

            <h2>5. Права пользователей</h2>
            <p>Вы имеете право:</p>
            <ul>
              <li>Получить доступ к своим данным</li>
              <li>Исправить неточные данные</li>
              <li>Удалить свои данные</li>
              <li>Отозвать согласие на обработку</li>
            </ul>

            <h2>6. Cookies</h2>
            <p>
              Мы используем cookies для улучшения работы сайта. Вы можете отключить cookies в настройках браузера.
            </p>

            <h2>7. Контакты</h2>
            <p>
              По вопросам обработки персональных данных: <a href="mailto:privacy@agency.com">privacy@agency.com</a>
            </p>
          </div>
        </div>
      </main>
      <InteractiveFooter />
    </>
  )
}
