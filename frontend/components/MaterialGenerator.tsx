'use client';

import FloatingChat from './FloatingChat';

export default function MaterialGenerator() {
    return (
        <div className="space-y-8 animate-fade-in">
            {/* Header */}
            <div className="glass rounded-3xl p-8 shadow-premium hover-lift">
                <div className="flex items-center gap-4 mb-3">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-glow">
                        <span className="text-3xl">📄</span>
                    </div>
                    <div>
                        <h2 className="text-4xl font-bold text-gradient">Generador de Material</h2>
                        <p className="text-slate-600 mt-1">Creación automática de contenido farmacéutico</p>
                    </div>
                </div>
            </div>

            {/* Coming Soon Card */}
            <div className="glass rounded-3xl p-12 shadow-premium text-center animate-scale-in">
                <div className="max-w-2xl mx-auto">
                    <div className="text-8xl mb-6 animate-bounce">🚀</div>
                    <h3 className="text-3xl font-bold text-slate-800 mb-4">Próximamente</h3>
                    <p className="text-lg text-slate-600 mb-8">
                        Esta funcionalidad está en desarrollo. Pronto podrás generar materiales farmacéuticos de forma automática con IA.
                    </p>

                    {/* Feature Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
                        <div className="glass rounded-2xl p-6 hover-lift">
                            <div className="text-4xl mb-3">📊</div>
                            <h4 className="font-bold text-slate-800 mb-2">Presentaciones</h4>
                            <p className="text-sm text-slate-600">Genera slides profesionales automáticamente</p>
                        </div>
                        <div className="glass rounded-2xl p-6 hover-lift">
                            <div className="text-4xl mb-3">📝</div>
                            <h4 className="font-bold text-slate-800 mb-2">Documentos</h4>
                            <p className="text-sm text-slate-600">Crea informes y documentación técnica</p>
                        </div>
                        <div className="glass rounded-2xl p-6 hover-lift">
                            <div className="text-4xl mb-3">🎨</div>
                            <h4 className="font-bold text-slate-800 mb-2">Diseño</h4>
                            <p className="text-sm text-slate-600">Aplica branding y estilos corporativos</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Floating Chat */}
            <FloatingChat context="generator" />
        </div>
    );
}
