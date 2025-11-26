'use client';

import { useState } from 'react';
import ClaimsValidator from '@/components/ClaimsValidator';
import MaterialGenerator from '@/components/MaterialGenerator';
import ChatCopilot from '@/components/ChatCopilot';
import { Pill, FileText, LayoutGrid } from 'lucide-react';
import { type PPTXValidationResponse } from '@/lib/api';

type Page = 'validator' | 'generator';

export default function Home() {
  const [currentPage, setCurrentPage] = useState<Page>('validator');
  const [validationResults, setValidationResults] = useState<PPTXValidationResponse | null>(null);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans selection:bg-indigo-100 selection:text-indigo-700">

      {/* Top Navigation Bar */}
      <nav className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-slate-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
              <Pill className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">Inphormed</h1>
              <p className="text-xs text-slate-500 font-medium tracking-wide uppercase">Medical Intelligence</p>
            </div>
          </div>

          <div className="flex bg-slate-100/50 p-1 rounded-xl border border-slate-200/50">
            <button
              onClick={() => setCurrentPage('validator')}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200
                ${currentPage === 'validator'
                  ? 'bg-white text-indigo-600 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/50'
                }
              `}
            >
              <LayoutGrid className="w-4 h-4" />
              Validator
            </button>
            <button
              onClick={() => setCurrentPage('generator')}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200
                ${currentPage === 'generator'
                  ? 'bg-white text-indigo-600 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/50'
                }
              `}
            >
              <FileText className="w-4 h-4" />
              Generator
            </button>
          </div>

          <div className="flex items-center gap-3">
            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></div>
            <span className="text-xs font-medium text-slate-500">System Operational</span>
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {currentPage === 'validator' && (
          <div className="animate-fade-in">
            <ClaimsValidator onValidationComplete={setValidationResults} />
          </div>
        )}
        {currentPage === 'generator' && (
          <div className="animate-fade-in">
            <MaterialGenerator />
          </div>
        )}
      </main>

      {/* Floating Chat Copilot */}
      <ChatCopilot context={currentPage} validationContext={validationResults} />

    </div>
  );
}
