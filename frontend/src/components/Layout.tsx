import { NavLink, Outlet } from 'react-router-dom'

const link = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-1.5 text-sm font-medium transition ${
    isActive ? 'bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900' : 'hover:bg-stone-200 dark:hover:bg-stone-800'
  }`

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 border-b border-stone-200 bg-stone-50/90 backdrop-blur dark:border-stone-800 dark:bg-stone-950/90">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <NavLink to="/" className="flex items-center gap-2 font-bold tracking-tight">
            <span className="flex flex-col gap-0.5 rounded-md bg-stone-800 px-1 py-1">
              <span className="size-2 rounded-full bg-stop" />
              <span className="size-2 rounded-full bg-warn" />
              <span className="size-2 rounded-full bg-go" />
            </span>
            <span className="hidden sm:inline">TrueTinFoilHat</span>
          </NavLink>
          <nav className="flex gap-1">
            <NavLink to="/" end className={link}>Analizar</NavLink>
            <NavLink to="/gallery" className={link}>Galería</NavLink>
            <NavLink to="/settings" className={link}>Ajustes</NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>
      <footer className="border-t border-stone-200 py-4 text-center text-xs text-stone-500 dark:border-stone-800">
        Análisis automático con IA: orientativo, no es asesoría legal. Versiones anteriores vía Internet Archive Wayback Machine.
      </footer>
    </div>
  )
}
