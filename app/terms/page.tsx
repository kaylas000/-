import InteractiveFooter from '@/components/InteractiveFooter'

export const metadata = {
  title: 'Условия использования | Premium Agency',
  description: 'Правила и условия использования сайта',
}

export default function TermsPage() {
  return (
    <>
      <main className="min-h-screen pt-32 px-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-6xl font-black mb-8">Условия использования</h1>
          
          <div className="prose prose-invert prose-lg max-w-none">
            <p className="text-accent text-xl mb-8">
              Дата вступления в силу: {new Date().toLocaleDateString('ru-RU')}
            </p>

            <h2>1. Принятие условий</h2>
            <p>
              Используя наш сайт, вы соглашаетесь с настоящими Условиями использования.
            </p>

            <h2>2. Услуги</h2>
            <p>Мы предоставляем следующие услуги:</p>
            <ul>
              <li>Разработка веб-приложений</li>
              <li>Мобильная разработка</li>
              <li>AI и Machine Learning интеграция</li>
              <li>Брендинг и дизайн</li>
              <li>DevOps и инфраструктура</li>
            </ul>

            <h2>3. Интеллектуальная собственность</h2>
            <p>
              Все материалы сайта защищены авторским правом. Использование без письменного разрешения запрещено.
            </p>

            <h2>4. Ограничение ответственности</h2>
            <p>
              Мы не несем ответственности за косвенные убытки, возникшие в результате использования наших услуг.
            </p>

            <h2>5. Конфиденциальность</h2>
            <p>
              Обработка персональных данных осуществляется в соответствии с <a href="/privacy">Политикой конфиденциальности</a>.
            </p>

            <h2>6. Изменения условий</h2>
            <p>
              Мы оставляем за собой право изменять настоящие Условия. Изменения вступают в силу с момента публикации.
            </p>

            <h2>7. Применимое право</h2>
            <p>
              Настоящие Условия регулируются законодательством Российской Федерации.
            </p>

            <h2>8. Контакты</h2>
            <p>
              По всем вопросам: <a href="mailto:legal@agency.com">legal@agency.com</a>
            </p>
          </div>
        </div>
      </main>
      <InteractiveFooter />
    </>
  )
}
