'use client';

import { useState, useRef } from 'react';
import { validatePPTX, downloadBase64File, type PPTXValidationResponse } from '@/lib/api';
import FloatingChat from './FloatingChat';

export default function ClaimsValidator() {
    const [activeTab, setActiveTab] = useState<'pptx' | 'text'>('pptx');
    const [file, setFile] = useState<File | null>(null);
    const [topk, setTopk] = useState(8);
    const [thrGreen, setThrGreen] = useState(0.82);
    const [thrYellow, setThrYellow] = useState(0.70);
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<PPTXValidationResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [claimText, setClaimText] = useState('');
    const [citationText, setCitationText] = useState('');
    const [dragActive, setDragActive] = useState(false);

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            setFile(e.dataTransfer.files[0]);
            setResults(null);
            setError(null);
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setResults(null);
            setError(null);
        }
    };

    const handleValidatePPTX = async () => {
        if (!file) {
            setError('Por favor selecciona un archivo PPTX');
            return;
        }

        setLoading(true);
        setError(null);
        setResults(null);

        try {
            const data = await validatePPTX(file, topk, thrGreen, thrYellow, true);
            setResults(data);
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || 'Error al validar el PPTX');
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadPPTX = () => {
        if (results?.annotated_pptx_b64 && results?.annotated_file_name) {
            downloadBase64File(
                results.annotated_pptx_b64,
                results.annotated_file_name,
                'application/vnd.openxmlformats-officedocument.presentationml.presentation'
            );
        }
    };

    const handleValidateText = () => {
        if (!claimText || !citationText) {
            setError('Debes rellenar el Claim y la Cita');
            return;
        }
        setError('Función de validación de texto simple en desarrollo...');
    };

    const getStatusEmoji = (status: string) => {
        switch (status) {
            case 'green': return '🟢';
            case 'yellow': return '🟡';
            case 'red': return '🔴';
            default: return '⚪';
        }
    };

    return (
        <div className="space-y-8 animate-fade-in">
            {/* Header */}
            <div className="glass rounded-3xl p-8 shadow-premium hover-lift">
                <div className="flex items-center gap-4 mb-3">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-glow">
                        <span className="text-3xl">🔬</span>
                    </div>
                    <div>
                        <h2 className="text-4xl font-bold text-gradient">Validador de Claims</h2>
                        <p className="text-slate-600 mt-1">Validación científica con evidencia farmacéutica</p>
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="glass rounded-2xl p-2 shadow-premium inline-flex gap-2">
                <button
                    onClick={() => setActiveTab('pptx')}
                    className={`px-8 py-3 rounded-xl font-semibold transition-all duration-300 ${activeTab === 'pptx'
                        ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-glow'
                        : 'text-slate-600 hover:bg-white/50'
                        }`}
                >
                    <span className="mr-2">📄</span>
                    Subir PPTX
                </button>
                <button
                    onClick={() => setActiveTab('text')}
                    className={`px-8 py-3 rounded-xl font-semibold transition-all duration-300 ${activeTab === 'text'
                        ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-glow'
                        : 'text-slate-600 hover:bg-white/50'
                        }`}
                >
                    <span className="mr-2">✍️</span>
                    Pegar Texto
                </button>
            </div>

            {/* PPTX Tab */}
            {activeTab === 'pptx' && (
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 animate-slide-in-up">
                    {/* Main Area */}
                    <div className="lg:col-span-3 space-y-6">
                        {/* Upload Card */}
                        <div className="glass rounded-3xl p-8 shadow-premium hover-lift">
                            <h3 className="text-xl font-bold text-slate-800 mb-6 flex items-center gap-2">
                                <span className="text-2xl">📎</span>
                                Subir Archivo PPTX
                            </h3>

                            <label
                                onDragEnter={handleDrag}
                                onDragLeave={handleDrag}
                                onDragOver={handleDrag}
                                onDrop={handleDrop}
                                htmlFor="pptx-upload"
                                className={`
                                    block relative border-3 border-dashed rounded-2xl p-12 text-center transition-all duration-300 cursor-pointer
                                    ${dragActive
                                        ? 'border-blue-500 bg-blue-50 scale-105'
                                        : 'border-slate-300 hover:border-blue-400 hover:bg-slate-50'
                                    }
                                `}
                            >
                                <input
                                    type="file"
                                    accept=".pptx"
                                    onChange={handleFileChange}
                                    className="hidden"
                                    id="pptx-upload"
                                />
                                <div className="pointer-events-none">
                                    <div className="text-7xl mb-4 animate-bounce">{file ? '✅' : '📎'}</div>
                                    <p className="text-lg font-semibold text-slate-700 mb-2">
                                        {file ? file.name : 'Arrastra tu archivo PPTX aquí'}
                                    </p>
                                    <p className="text-sm text-slate-500">
                                        o haz clic para seleccionar
                                    </p>
                                </div>
                            </label>

                            <button
                                onClick={handleValidatePPTX}
                                disabled={!file || loading}
                                className={`
                                    w-full mt-6 px-8 py-4 rounded-2xl font-bold text-lg transition-all duration-300
                                    ${!file || loading
                                        ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                                        : 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-glow hover:shadow-premium hover:scale-105'
                                    }
                                `}
                            >
                                {loading ? (
                                    <div className="flex items-center justify-center gap-3">
                                        <div className="w-6 h-6 border-3 border-white border-t-transparent rounded-full animate-spin"></div>
                                        <span>Validando... (1-2 minutos)</span>
                                    </div>
                                ) : (
                                    <div className="flex items-center justify-center gap-2">
                                        <span className="text-2xl">🔍</span>
                                        <span>Validar PPTX</span>
                                    </div>
                                )}
                            </button>
                        </div>

                        {/* Error */}
                        {error && (
                            <div className="glass rounded-2xl p-6 border-l-4 border-red-500 bg-red-50/50 animate-scale-in">
                                <div className="flex items-center gap-3">
                                    <span className="text-3xl">⚠️</span>
                                    <div>
                                        <strong className="text-red-700">Error:</strong>
                                        <p className="text-red-600">{error}</p>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Results */}
                        {results && (
                            <div className="glass rounded-3xl p-8 shadow-premium animate-scale-in">
                                <div className="flex items-center justify-between mb-6">
                                    <div>
                                        <h3 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
                                            <span>📊</span>
                                            Resultados
                                        </h3>
                                        <p className="text-slate-600 mt-1">
                                            <strong>{results.file_name}</strong> — {results.total_claims} claims detectados
                                        </p>
                                    </div>
                                    {results.annotated_pptx_b64 && (
                                        <button
                                            onClick={handleDownloadPPTX}
                                            className="px-6 py-3 rounded-xl bg-gradient-to-r from-green-500 to-emerald-600 text-white font-semibold shadow-glow hover:shadow-premium hover:scale-105 transition-all duration-300"
                                        >
                                            <span className="mr-2">⬇️</span>
                                            Descargar PPTX
                                        </button>
                                    )}
                                </div>

                                {results.results.length > 0 ? (
                                    <div className="overflow-x-auto rounded-2xl border border-slate-200">
                                        <table className="w-full">
                                            <thead className="bg-gradient-to-r from-slate-50 to-blue-50">
                                                <tr>
                                                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Dónde</th>
                                                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Estado</th>
                                                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Score</th>
                                                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Claim</th>
                                                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Cita</th>
                                                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">URL</th>
                                                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Snippet</th>
                                                </tr>
                                            </thead>
                                            <tbody className="bg-white divide-y divide-slate-100">
                                                {results.results.map((result, idx) => (
                                                    <tr key={idx} className="hover:bg-blue-50/50 transition-colors">
                                                        <td className="px-4 py-3 text-sm font-medium text-slate-700">{result.where}</td>
                                                        <td className="px-4 py-3">
                                                            <span className={`
                                                                inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold
                                                                ${result.status === 'green' ? 'bg-green-100 text-green-700' :
                                                                    result.status === 'yellow' ? 'bg-yellow-100 text-yellow-700' :
                                                                        'bg-red-100 text-red-700'}
                                                            `}>
                                                                {getStatusEmoji(result.status)} {result.status}
                                                            </span>
                                                        </td>
                                                        <td className="px-4 py-3 text-sm font-mono font-bold text-indigo-600">
                                                            {result.best_score.toFixed(3)}
                                                        </td>
                                                        <td className="px-4 py-3 text-sm text-slate-600 max-w-xs truncate" title={result.text}>
                                                            {result.text.substring(0, 120)}{result.text.length > 120 ? '…' : ''}
                                                        </td>
                                                        <td className="px-4 py-3 text-sm text-slate-600 max-w-xs truncate" title={result.best_title}>
                                                            {result.best_title.substring(0, 100)}{result.best_title.length > 100 ? '…' : ''}
                                                        </td>
                                                        <td className="px-4 py-3">
                                                            {result.best_url ? (
                                                                <a
                                                                    href={result.best_url}
                                                                    target="_blank"
                                                                    rel="noopener noreferrer"
                                                                    className="text-blue-600 hover:text-blue-800 font-semibold hover:underline"
                                                                >
                                                                    Ver →
                                                                </a>
                                                            ) : (
                                                                <span className="text-slate-400">—</span>
                                                            )}
                                                        </td>
                                                        <td className="px-4 py-3 text-sm text-slate-600 max-w-xs truncate" title={result.best_verdict}>
                                                            {result.best_verdict}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                ) : (
                                    <div className="text-center py-12 text-slate-500">
                                        <span className="text-5xl mb-3 block">📭</span>
                                        Sin resultados
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Sidebar Parameters */}
                    <div className="space-y-4">
                        <div className="glass rounded-3xl p-6 shadow-premium sticky top-4">
                            <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
                                <span className="text-xl">⚙️</span>
                                Parámetros
                            </h3>

                            <div className="space-y-5">
                                <div>
                                    <label className="block text-sm font-semibold text-slate-700 mb-2">Top-K</label>
                                    <input
                                        type="number"
                                        min="1"
                                        max="20"
                                        value={topk}
                                        onChange={(e) => setTopk(parseInt(e.target.value))}
                                        className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all outline-none font-semibold"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-semibold text-slate-700 mb-2">Umbral Verde</label>
                                    <input
                                        type="number"
                                        min="0"
                                        max="1"
                                        step="0.01"
                                        value={thrGreen}
                                        onChange={(e) => setThrGreen(parseFloat(e.target.value))}
                                        className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-green-500 focus:ring-4 focus:ring-green-100 transition-all outline-none font-semibold"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-semibold text-slate-700 mb-2">Umbral Amarillo</label>
                                    <input
                                        type="number"
                                        min="0"
                                        max="1"
                                        step="0.01"
                                        value={thrYellow}
                                        onChange={(e) => setThrYellow(parseFloat(e.target.value))}
                                        className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-yellow-500 focus:ring-4 focus:ring-yellow-100 transition-all outline-none font-semibold"
                                    />
                                </div>

                                <div className="bg-gradient-to-br from-slate-50 to-blue-50 p-4 rounded-xl border border-slate-200">
                                    <strong className="text-xs font-bold text-slate-700 uppercase block mb-3">Criterios:</strong>
                                    <ul className="space-y-2 text-sm">
                                        <li className="flex items-center gap-2">
                                            <span className="text-lg">🔴</span>
                                            <span className="text-slate-600">score &lt; {thrYellow}</span>
                                        </li>
                                        <li className="flex items-center gap-2">
                                            <span className="text-lg">🟡</span>
                                            <span className="text-slate-600">{thrYellow} ≤ score &lt; {thrGreen}</span>
                                        </li>
                                        <li className="flex items-center gap-2">
                                            <span className="text-lg">🟢</span>
                                            <span className="text-slate-600">score ≥ {thrGreen}</span>
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Text Tab */}
            {activeTab === 'text' && (
                <div className="glass rounded-3xl p-8 shadow-premium animate-slide-in-up">
                    <h3 className="text-xl font-bold text-slate-800 mb-6 flex items-center gap-2">
                        <span className="text-2xl">✍️</span>
                        Validar Texto Simple
                    </h3>

                    <div className="space-y-6">
                        <div>
                            <label className="block text-sm font-semibold text-slate-700 mb-2">Claim</label>
                            <textarea
                                value={claimText}
                                onChange={(e) => setClaimText(e.target.value)}
                                placeholder="Escribe el claim que quieres validar..."
                                className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all outline-none resize-none"
                                rows={4}
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-semibold text-slate-700 mb-2">Cita / Referencia</label>
                            <textarea
                                value={citationText}
                                onChange={(e) => setCitationText(e.target.value)}
                                placeholder="Pega la cita o referencia científica..."
                                className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all outline-none resize-none"
                                rows={4}
                            />
                        </div>

                        <button
                            onClick={handleValidateText}
                            className="w-full px-8 py-4 rounded-2xl font-bold text-lg bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-glow hover:shadow-premium hover:scale-105 transition-all duration-300"
                        >
                            <span className="mr-2">🔍</span>
                            Validar Texto
                        </button>

                        {error && activeTab === 'text' && (
                            <div className="glass rounded-2xl p-6 border-l-4 border-blue-500 bg-blue-50/50 animate-scale-in">
                                <div className="flex items-center gap-3">
                                    <span className="text-3xl">ℹ️</span>
                                    <p className="text-blue-700">{error}</p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Floating Chat */}
            <FloatingChat context="validator" />
        </div>
    );
}
