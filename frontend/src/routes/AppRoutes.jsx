import { Routes, Route } from 'react-router-dom';
import MainLayout from '../layouts/MainLayout';
import AuthLayout from '../layouts/AuthLayout';
import ProtectedRoute from '../components/common/ProtectedRoute';

import Home from '../pages/Home';
import Login from '../pages/Login';
import Register from '../pages/Register';
import Dashboard from '../pages/Dashboard';
import PatientProfile from '../pages/PatientProfile';
import SymptomAssessment from '../pages/SymptomAssessment';
import TestRecommendations from '../pages/TestRecommendations';
import ReportManagement from '../pages/ReportManagement';
import PredictionResults from '../pages/PredictionResults';
import AssessmentHistory from '../pages/AssessmentHistory';
import AccountSettings from '../pages/AccountSettings';
import NotFound from '../pages/NotFound';

export default function AppRoutes() {
  return (
    <Routes>
      {/* Public Home Page wrapped in MainLayout */}
      <Route element={<MainLayout />}>
        <Route path="/" element={<Home />} />
      </Route>

      {/* Authentication Pages wrapped in AuthLayout */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>

      {/* Authenticated Clinical Workflow Pages wrapped in MainLayout & ProtectedRoute */}
      <Route
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/patient-profile" element={<PatientProfile />} />
        <Route path="/symptom-assessment" element={<SymptomAssessment />} />
        <Route path="/test-recommendations" element={<TestRecommendations />} />
        <Route path="/report-management" element={<ReportManagement />} />
        <Route path="/prediction-results" element={<PredictionResults />} />
        <Route path="/assessment-history" element={<AssessmentHistory />} />
        <Route path="/account-settings" element={<AccountSettings />} />
      </Route>

      {/* 404 Catch-All */}
      <Route element={<MainLayout />}>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
