import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopNav } from './TopNav';

export const AppShell: React.FC = () => {
  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <div className="flex-1 ml-64 flex flex-col min-w-0">
        <TopNav />
        <main className="flex-1 mt-16 p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
