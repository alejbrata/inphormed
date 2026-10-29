'use client';

import { useState } from 'react';
import { validatePPTX, downloadBase64File, type PPTXValidationResponse } from '@/lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import {
    UploadCloud, FileText, CheckCircle2, AlertTriangle, XCircle,
    Download, Search, ArrowRight, FileType, Microscope, Sliders, Sparkles
} from 'lucide-react';

interface ClaimsValidatorProps {
    onValidationComplete?: (results: PPTXValidationResponse) => void;
}

export default function ClaimsValidator({ onValidationComplete }: ClaimsValidatorProps) {
    const [activeTab, setActiveTab] = useState<'pptx' | 'text'>('pptx');
    const [file, setFile] = useState<File | null>(null);
    const [topk, setTopk] = useState(8);
    const [thrGreen, setThrGreen] = useState(0.82);
    const [thrYellow, setThrYellow] = useState(0.70);
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<PPTXValidationResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
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
        if (!file) return;
        setLoading(true);
        setError(null);
        setResults(null);

        try {
            const data = await validatePPTX(file, topk, thrGreen, thrYellow, true);
            setResults(data);
            if (onValidationComplete) {
                onValidationComplete(data);
            }
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

    const container = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1
            }
        }
    };

    const item = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0 }
    };

    return (
        <div className="max-w-7xl mx-auto space-y-8 pb-20">
            {/* Header Section */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 tracking-tight flex items-center gap-3">
                        <Microscope className="w-8 h-8 text-indigo-600" />
                        Clinical Validation
                    </h1>
                    <p className="text-slate-500 mt-1">AI-powered scientific evidence verification</p>
                </div>
                <div className="flex bg-white p-1 rounded-xl border border-slate-200 shadow-sm">
                    <button
                        onClick={() => setActiveTab('pptx')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'pptx'
                            ? 'bg-indigo-50 text-indigo-700 shadow-sm'
                            : 'text-slate-500 hover:text-slate-700'
                            }`}
                    >
                        Presentation
                    </button>
                    <button
                        onClick={() => setActiveTab('text')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'text'
                            ? 'bg-indigo-50 text-indigo-700 shadow-sm'
                            : 'text-slate-500 hover:text-slate-700'
                            }`}
                    >
                        Text Analysis
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Left Column: Input & Config */}
                <div className="lg:col-span-4 space-y-6">
                    {/* Uploader Card */}
                    <div className="bg-white rounded-3xl p-1 border border-slate-200 shadow-soft overflow-hidden">
                        <div
                            className={`
                                relative rounded-[20px] p-8 text-center transition-all duration-500 ease-out
                                ${dragActive ? 'bg-indigo-50/50 border-indigo-400' : 'bg-slate-50/50 border-transparent'}
                                border-2 border-dashed group
                            `}
                            onDragEnter={handleDrag}
                            onDragLeave={handleDrag}
                            onDragOver={handleDrag}
                            onDrop={handleDrop}
                        >
                            <input
                                type="file"
                                accept=".pptx"
                                onChange={handleFileChange}
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                            />

                            <div className={`transition-transform duration-500 ${dragActive ? 'scale-110' : 'group-hover:scale-105'}`}>
                                <div className={`
                                    w-20 h-20 mx-auto rounded-full flex items-center justify-center mb-6 transition-colors duration-500
                                    ${file ? 'bg-teal-100 text-teal-600' : 'bg-indigo-100 text-indigo-600'}
                                `}>
                                    {file ? <CheckCircle2 className="w-10 h-10" /> : <UploadCloud className="w-10 h-10" />}
                                </div>
                            </div>

                            <h3 className="text-lg font-semibold text-slate-900 mb-2">
                                {file ? file.name : 'Upload Presentation'}
                            </h3>
                            <p className="text-sm text-slate-500 max-w-[200px] mx-auto">
                                {file ? 'Ready to validate' : 'Drag & drop your .pptx file here or click to browse'}
                            </p>
                        </div>

                        <div className="p-6">
                            <button
                                onClick={handleValidatePPTX}
                                disabled={!file || loading}
                                className={`
                                    w-full py-4 rounded-xl font-semibold text-white shadow-lg shadow-indigo-500/20
                                    flex items-center justify-center gap-2 transition-all duration-300
                                    ${!file || loading
                                        ? 'bg-slate-300 cursor-not-allowed shadow-none'
                                        : 'bg-indigo-600 hover:bg-indigo-700 hover:scale-[1.02]'
                                    }
                                `}
                            >
                                {loading ? (
                                    <>
                                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        <span>Analyzing...</span>
                                    </>
                                ) : (
                                    <>
                                        <Search className="w-5 h-5" />
                                        <span>Start Validation</span>
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    {/* Parameters Card */}
                    <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-soft">
                        <div className="flex items-center gap-2 mb-6 text-slate-800 font-semibold">
                            <Sliders className="w-5 h-5 text-indigo-600" />
                            Configuration
                        </div>

                        <div className="space-y-6">
                            <div>
                                <div className="flex justify-between text-sm mb-2">
                                    <span className="text-slate-600">Evidence Depth (Top-K)</span>
                                    <span className="font-mono text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">{topk}</span>
                                </div>
                                <input
                                    type="range" min="1" max="20" value={topk}
                                    onChange={(e) => setTopk(parseInt(e.target.value))}
                                    className="w-full h-2 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wider">Green Thr</label>
                                    <input
                                        type="number" step="0.01" value={thrGreen}
                                        onChange={(e) => setThrGreen(parseFloat(e.target.value))}
                                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 outline-none transition-all"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wider">Yellow Thr</label>
                                    <input
                                        type="number" step="0.01" value={thrYellow}
                                        onChange={(e) => setThrYellow(parseFloat(e.target.value))}
                                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-yellow-500/20 focus:border-yellow-500 outline-none transition-all"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Right Column: Results */}
                <div className="lg:col-span-8">
                    <AnimatePresence mode="wait">
                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                                className="bg-red-50 border border-red-100 rounded-2xl p-4 flex items-center gap-3 text-red-700 mb-6"
                            >
                                <XCircle className="w-6 h-6 flex-shrink-0" />
                                <p>{error}</p>
                            </motion.div>
                        )}

                        {!results && !loading && !error && (
                            <motion.div
                                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                                className="h-full min-h-[400px] flex flex-col items-center justify-center text-slate-400 border-2 border-dashed border-slate-200 rounded-3xl bg-slate-50/50"
                            >
                                <FileType className="w-16 h-16 mb-4 opacity-50" />
                                <p>Results will appear here</p>
                            </motion.div>
                        )}

                        {results && (
                            <motion.div
                                variants={container} initial="hidden" animate="show"
                                className="space-y-6"
                            >
                                {/* Results Header */}
                                <div className="flex items-center justify-between bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
                                    <div>
                                        <h2 className="font-bold text-slate-900">Analysis Report</h2>
                                        <p className="text-sm text-slate-500">{results.total_claims} claims analyzed in {results.file_name}</p>
                                    </div>
                                    {results.annotated_pptx_b64 && (
                                        <button
                                            onClick={handleDownloadPPTX}
                                            className="px-4 py-2 bg-teal-50 text-teal-700 hover:bg-teal-100 rounded-xl font-medium text-sm flex items-center gap-2 transition-colors"
                                        >
                                            <Download className="w-4 h-4" />
                                            Download Report
                                        </button>
                                    )}
                                </div>

                                {/* Finding Cards Grid */}
                                <div className="grid grid-cols-1 gap-4">
                                    {results.results.map((result, idx) => (
                                        <motion.div
                                            key={idx} variants={item}
                                            className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm hover:shadow-md transition-all group"
                                        >
                                            <div className="flex items-start justify-between gap-4 mb-4">
                                                <div className="flex items-center gap-3">
                                                    <span className={`
                                                        px-3 py-1 rounded-full text-xs font-bold border flex items-center gap-1.5
                                                        ${result.status === 'green' ? 'bg-teal-50 text-teal-700 border-teal-200' :
                                                            result.status === 'yellow' ? 'bg-yellow-50 text-yellow-700 border-yellow-200' :
                                                                'bg-red-50 text-red-700 border-red-200'}
                                                    `}>
                                                        <span className={`w-1.5 h-1.5 rounded-full ${result.status === 'green' ? 'bg-teal-500' :
                                                            result.status === 'yellow' ? 'bg-yellow-500' : 'bg-red-500'
                                                            }`} />
                                                        {result.status.toUpperCase()}
                                                    </span>
                                                    <span className="text-xs font-mono text-slate-400 bg-slate-50 px-2 py-1 rounded">
                                                        {result.where}
                                                    </span>
                                                </div>

                                                {/* Confidence Meter */}
                                                <div className="flex items-center gap-2" title={`Confidence Score: ${result.best_score.toFixed(3)}`}>
                                                    <div className="w-24 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                                        <div
                                                            className={`h-full rounded-full ${result.status === 'green' ? 'bg-teal-500' :
                                                                result.status === 'yellow' ? 'bg-yellow-500' : 'bg-red-500'
                                                                }`}
                                                            style={{ width: `${result.best_score * 100}%` }}
                                                        />
                                                    </div>
                                                    <span className="text-xs font-bold text-slate-700">{Math.round(result.best_score * 100)}%</span>
                                                </div>
                                            </div>

                                            <div className="grid md:grid-cols-2 gap-6">
                                                <div>
                                                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Original Claim</h4>
                                                    <p className="text-slate-800 font-medium leading-relaxed">"{result.text}"</p>
                                                </div>

                                                <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                                                    <h4 className="text-xs font-bold text-indigo-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                                                        <Sparkles className="w-3 h-3" />
                                                        AI Verification
                                                    </h4>
                                                    {result.best_url ? (
                                                        <>
                                                            <p className="text-sm text-slate-600 mb-3 line-clamp-3 italic">
                                                                "{result.best_verdict}"
                                                            </p>
                                                            <div className="flex items-center justify-between pt-2 border-t border-slate-200/60">
                                                                <span className="text-xs text-slate-500 truncate max-w-[200px]" title={result.best_title}>
                                                                    {result.best_title}
                                                                </span>
                                                                <a
                                                                    href={result.best_url} target="_blank" rel="noopener noreferrer"
                                                                    className="text-xs font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
                                                                >
                                                                    View Source <ArrowRight className="w-3 h-3" />
                                                                </a>
                                                            </div>
                                                        </>
                                                    ) : (
                                                        <p className="text-sm text-slate-400 italic">No sufficient evidence found.</p>
                                                    )}
                                                </div>
                                            </div>

                                            {/* Compliance Section */}
                                            {(result.compliance_status === 'fail' || result.compliance_status === 'pass') && (
                                                <div className={`mt-4 rounded-xl p-4 border ${result.compliance_status === 'pass'
                                                        ? 'bg-emerald-50 border-emerald-100'
                                                        : 'bg-rose-50 border-rose-100'
                                                    }`}>
                                                    <h4 className={`text-xs font-bold uppercase tracking-wider mb-2 flex items-center gap-1 ${result.compliance_status === 'pass' ? 'text-emerald-600' : 'text-rose-600'
                                                        }`}>
                                                        {result.compliance_status === 'pass' ? (
                                                            <CheckCircle2 className="w-3 h-3" />
                                                        ) : (
                                                            <AlertTriangle className="w-3 h-3" />
                                                        )}
                                                        Regulatory Compliance (Farmaindustria)
                                                    </h4>

                                                    {result.compliance_status === 'pass' ? (
                                                        <p className="text-sm text-emerald-800 font-medium">
                                                            Passes regulatory checks.
                                                        </p>
                                                    ) : (
                                                        <div className="space-y-1">
                                                            <p className="text-sm text-rose-800 font-bold">
                                                                Compliance Issue Detected:
                                                            </p>
                                                            <p className="text-sm text-rose-700 italic">
                                                                "{result.compliance_reason}"
                                                            </p>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </motion.div>
                                    ))}
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
}
