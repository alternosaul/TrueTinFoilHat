import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './index.css'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import AnalysisPage from './pages/AnalysisPage'
import DiffPage from './pages/DiffPage'
import GalleryPage from './pages/GalleryPage'
import CompanyPage from './pages/CompanyPage'
import SettingsPage from './pages/SettingsPage'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="analysis/:id" element={<AnalysisPage />} />
          <Route path="comparison/:id" element={<DiffPage />} />
          <Route path="gallery" element={<GalleryPage />} />
          <Route path="company/:id" element={<CompanyPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
