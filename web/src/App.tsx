import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Home from './pages/Home'
import Meal from './pages/Meal'
import Weight from './pages/Weight'
import Weather from './pages/Weather'
import Schedule from './pages/Schedule'
import Diary from './pages/Diary'
import Email from './pages/Email'
import Report from './pages/Report'
import Settings from './pages/Settings'
import Login from './pages/Login'
import Onboarding from './pages/Onboarding'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/meal" element={<Meal />} />
            <Route path="/weight" element={<Weight />} />
            <Route path="/weather" element={<Weather />} />
            <Route path="/schedule" element={<Schedule />} />
            <Route path="/diary" element={<Diary />} />
            <Route path="/email" element={<Email />} />
            <Route path="/report" element={<Report />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
