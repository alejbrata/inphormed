'use client';

import { useState } from 'react';
import ClaimsValidator from '@/components/ClaimsValidator';
import MaterialGenerator from '@/components/MaterialGenerator';

type Page = 'validator' | 'generator';

const navigation = [
  { id: 'validator' as Page, name: 'Validador de Claims', icon: '🔬', description: 'Validación científica con IA' },
  { id: 'generator' as Page, name: 'Generador de Material', icon: '📄', description: 'Creación automática de contenido' },
];

export default function Home() {
  const [currentPage, setCurrentPage] = useState<Page>('validator');

  return (
    <div className="min-h-screen flex relative overflow-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute top-0 -left-4 w-96 h-96 bg-purple-300 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob"></div>
        <div className="absolute top-0 -right-4 w-96 h-96 bg-blue-300 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>
        <div className="absolute -bottom-8 left-20 w-96 h-96 bg-indigo-300 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-4000"></div>
      </div>

      {/* Glassmorphism Sidebar */}
      <aside className="w-80 glass-dark p-8 shadow-premium animate-slide-in-left relative overflow-hidden">
        {/* Decorative gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600/20 via-indigo-600/20 to-purple-600/20 pointer-events-none"></div>

        <div className="relative z-10">
          {/* Logo Section */}
          <div className="mb-12 animate-scale-in">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center shadow-glow">
                <span className="text-2xl">💊</span>
              </div>
              <div>
                <h1 className="text-3xl font-bold text-white tracking-tight">Inphormed</h1>
                <p className="text-blue-200 text-sm font-medium">Pharmaceutical AI</p>
              </div>
            </div>
            <div className="h-1 w-20 bg-gradient-to-r from-blue-400 to-indigo-500 rounded-full"></div>
          </div>

          {/* Navigation */}
          <nav className="space-y-3">
            {navigation.map((item, index) => (
              <button
                key={item.id}
                onClick={() => setCurrentPage(item.id)}
                className={`
                  w-full text-left px-5 py-4 rounded-2xl transition-all duration-300 group
                  animate-slide-in-left
                  ${currentPage === item.id
                    ? 'glass shadow-glow scale-105'
                    : 'hover:glass-dark hover:scale-102 hover:shadow-premium'
                  }
                `}
                style={{ animationDelay: `${index * 100}ms` }}
              >
                <div className="flex items-center gap-4">
                  <div className={`
                    text-3xl transition-transform duration-300 group-hover:scale-110
                    ${currentPage === item.id ? 'animate-bounce' : ''}
                  `}>
                    {item.icon}
                  </div>
                  <div className="flex-1">
                    <div className={`
                      font-semibold transition-colors
                      ${currentPage === item.id ? 'text-white' : 'text-blue-100'}
                    `}>
                      {item.name}
                    </div>
                    <div className="text-xs text-blue-300 mt-0.5">{item.description}</div>
                  </div>
                  {currentPage === item.id && (
                    <div className="w-2 h-2 rounded-full bg-green-400 shadow-glow animate-pulse"></div>
                  )}
                </div>
              </button>
            ))}
          </nav>

          {/* Backend Status */}
          <div className="mt-auto pt-8">
            <div className="glass rounded-2xl p-4 border border-white/10">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse shadow-glow"></div>
                <span className="text-xs font-semibold text-blue-100">Backend Connected</span>
              </div>
              <p className="text-xs text-blue-300 font-mono truncate">
                {process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}
              </p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-8 overflow-auto custom-scrollbar">
        <div className="max-w-7xl mx-auto animate-slide-in-up">
          {currentPage === 'validator' && <ClaimsValidator />}
          {currentPage === 'generator' && <MaterialGenerator />}
        </div>
      </main>

      <style jsx>{`
        @keyframes blob {
          0%, 100% { transform: translate(0, 0) scale(1); }
          25% { transform: translate(20px, -50px) scale(1.1); }
          50% { transform: translate(-20px, 20px) scale(0.9); }
          75% { transform: translate(50px, 50px) scale(1.05); }
        }
        .animate-blob {
          animation: blob 7s infinite;
        }
        .animation-delay-2000 {
          animation-delay: 2s;
        }
        .animation-delay-4000 {
          animation-delay: 4s;
        }
        .scale-102 {
          transform: scale(1.02);
        }
      `}</style>
    </div>
  );
}

