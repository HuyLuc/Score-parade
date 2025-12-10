import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginView from './views/LoginView';
import RegisterView from './views/RegisterView';
import ListOfCandidatesView from './views/ListOfCandidatesView';
import CreateCandidateView from './views/CreateCandidateView';
import ConfigurationView from './views/ConfigurationView';
import BaremView from './views/BaremView';
import ObservationView from './views/ObservationView';
import EndOfSectionView from './views/EndOfSectionView';
import SummaryView from './views/SummaryView';

const App: React.FC = () => {
  const token = localStorage.getItem('token');
  const defaultPath = token ? '/candidates' : '/login';

  const requireAuth = (element: JSX.Element) =>
    token ? element : <Navigate to="/login" replace />;

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to={defaultPath} replace />} />
        <Route path="/login" element={<LoginView />} />
        <Route path="/register" element={<RegisterView />} />
        <Route
          path="/candidates"
          element={requireAuth(<ListOfCandidatesView />)}
        />
        <Route
          path="/candidates/create"
          element={requireAuth(<CreateCandidateView />)}
        />
        <Route
          path="/configuration"
          element={requireAuth(<ConfigurationView />)}
        />
        <Route path="/barem" element={requireAuth(<BaremView />)} />
        <Route path="/observation" element={requireAuth(<ObservationView />)} />
        <Route
          path="/end-of-section"
          element={requireAuth(<EndOfSectionView />)}
        />
        <Route path="/summary" element={requireAuth(<SummaryView />)} />
        <Route path="*" element={<Navigate to={defaultPath} replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;

