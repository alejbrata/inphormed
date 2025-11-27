'use client';

import { useState, useRef, useEffect } from 'react';
import FloatingChat from './FloatingChat';
import { motion, AnimatePresence } from 'framer-motion';
import { UploadCloud, FileText, Play, Pause, Mic2, Sparkles, CheckCircle2, AlertTriangle, Headphones, FileType, Presentation, Download } from 'lucide-react';
import { generatePodcast, generateSummary, generateSlides, type PodcastResponse, type SummaryResponse } from '@/lib/api';

export default function MaterialGenerator() {
    const [activeMode, setActiveMode] = useState<'podcast' | 'summary' | 'slides'>('podcast');
    const [file, setFile] = useState<File | null>(null);
    const [textInput, setTextInput] = useState(''); // For slides
    const [numSlides, setNumSlides] = useState(5); // Default 5 slides
    const [loading, setLoading] = useState(false);

    // Results
    const [podcastResult, setPodcastResult] = useState<PodcastResponse | null>(null);
    const [summaryResult, setSummaryResult] = useState<SummaryResponse | null>(null);
    const [slidesResult, setSlidesResult] = useState<boolean>(false); // Just to show success state

    const [error, setError] = useState<string | null>(null);
    const [dragActive, setDragActive] = useState(false);
    const [isPlaying, setIsPlaying] = useState(false);

    // Audio ref
    const audioRef = useRef<HTMLAudioElement | null>(null);

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
            const droppedFile = e.dataTransfer.files[0];
            const validTypes = activeMode === 'slides'
                ? ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"]
                : ["application/pdf"];

            if (validTypes.includes(droppedFile.type) || (activeMode === 'slides' && droppedFile.name.endsWith('.docx'))) {
                setFile(droppedFile);
                setTextInput(''); // Clear text if file dropped
                resetResults();
            } else {
                setError("Por favor, sube un archivo válido (PDF o Word).");
            }
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0];
            const validTypes = activeMode === 'slides'
                ? ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"]
                : ["application/pdf"];

            if (validTypes.includes(selectedFile.type) || (activeMode === 'slides' && selectedFile.name.endsWith('.docx'))) {
                setFile(selectedFile);
                setTextInput('');
                resetResults();
            } else {
                setError("Por favor, sube un archivo válido (PDF o Word).");
            }
        }
    };

    const resetResults = () => {
        setPodcastResult(null);
        setSummaryResult(null);
        setSlidesResult(false);
        setError(null);
        setIsPlaying(false);
    };

    const handleGenerate = async (mode: 'podcast' | 'summary' | 'slides') => {
        if (mode !== 'slides' && !file) return;
        if (mode === 'slides' && !textInput.trim() && !file) {
            setError("Por favor, introduce texto o sube un archivo.");
            return;
        }

        setLoading(true);
        setActiveMode(mode);
        setError(null);

        try {
            if (mode === 'podcast' && file) {
                const data = await generatePodcast(file);
                setPodcastResult(data);
                setSummaryResult(null);
                setSlidesResult(false);
            } else if (mode === 'summary' && file) {
                const data = await generateSummary(file);
                setSummaryResult(data);
                setPodcastResult(null);
                setSlidesResult(false);
            } else if (mode === 'slides') {
                const blob = await generateSlides(textInput, file, numSlides);
                // Trigger download
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'generated_presentation.pptx';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                setSlidesResult(true);
                setPodcastResult(null);
                setSummaryResult(null);
            }
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.detail || "Error al generar el contenido. Inténtalo de nuevo.");
        } finally {
            setLoading(false);
        }
    };

    const togglePlay = () => {
        if (audioRef.current) {
            if (isPlaying) {
                audioRef.current.pause();
            } else {
                audioRef.current.play();
            }
            setIsPlaying(!isPlaying);
        }
    };

    useEffect(() => {
        if (podcastResult && podcastResult.audio_base64) {
            setIsPlaying(false);
        }
    }, [podcastResult]);

    return (
        <div className="space-y-8 animate-fade-in pb-20">
            {/* Header */}
            <div className="glass rounded-3xl p-8 shadow-premium hover-lift flex flex-col md:flex-row items-center justify-between gap-6">
                <div className="flex items-center gap-4">
                    <div className={`
                        w-16 h-16 rounded-2xl flex items-center justify-center shadow-glow text-white transition-colors duration-500
                        ${activeMode === 'podcast' ? 'bg-gradient-to-br from-indigo-500 to-purple-600' :
                            activeMode === 'summary' ? 'bg-gradient-to-br from-teal-500 to-emerald-600' :
                                'bg-gradient-to-br from-blue-500 to-cyan-600'}
                    `}>
                        {activeMode === 'podcast' ? <Mic2 className="w-8 h-8" /> :
                            activeMode === 'summary' ? <FileText className="w-8 h-8" /> :
                                <Presentation className="w-8 h-8" />}
                    </div>
                    <div>
                        <h2 className="text-4xl font-bold text-gradient">
                            {activeMode === 'podcast' ? 'Podcast Generator' :
                                activeMode === 'summary' ? 'Executive Summary' :
                                    'Slide Deck Generator'}
                        </h2>
                        <p className="text-slate-600 mt-1">
                            {activeMode === 'podcast' ? 'Convierte papers científicos en audio-resúmenes atractivos' :
                                activeMode === 'summary' ? 'Obtén los puntos clave y conclusiones en segundos' :
                                    'Crea presentaciones PowerPoint a partir de texto o documentos'}
                        </p>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Left Column: Input */}
                <div className="lg:col-span-5 space-y-6">
                    <div className="bg-white rounded-3xl p-1 border border-slate-200 shadow-soft overflow-hidden">

                        {/* INPUT AREA: PDF UPLOAD OR TEXTAREA */}
                        {activeMode === 'slides' ? (
                            <div className="p-6 space-y-4">
                                {/* Toggle between File and Text */}
                                <div className="flex gap-2 p-1 bg-slate-100 rounded-xl mb-4">
                                    <button
                                        onClick={() => { setFile(null); setTextInput(''); }}
                                        className={`flex-1 py-2 rounded-lg text-sm font-bold transition-all ${!textInput && file ? 'bg-white shadow-sm text-blue-600' : 'text-slate-500 hover:text-slate-700'}`}
                                    >
                                        Subir Archivo
                                    </button>
                                    <button
                                        onClick={() => { setFile(null); }}
                                        className={`flex-1 py-2 rounded-lg text-sm font-bold transition-all ${textInput || (!file && !textInput) ? 'bg-white shadow-sm text-blue-600' : 'text-slate-500 hover:text-slate-700'}`}
                                    >
                                        Pegar Texto
                                    </button>
                                </div>

                                {!textInput && (
                                    <div
                                        className={`
                                            relative rounded-[20px] p-8 text-center transition-all duration-500 ease-out
                                            ${dragActive ? 'bg-blue-50/50 border-blue-400' : 'bg-slate-50/50 border-transparent'}
                                            border-2 border-dashed group
                                        `}
                                        onDragEnter={handleDrag}
                                        onDragLeave={handleDrag}
                                        onDragOver={handleDrag}
                                        onDrop={handleDrop}
                                    >
                                        <input
                                            type="file"
                                            accept=".pdf,.docx,.txt"
                                            onChange={handleFileChange}
                                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                                        />

                                        <div className={`transition-transform duration-500 ${dragActive ? 'scale-110' : 'group-hover:scale-105'}`}>
                                            <div className={`
                                                w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-4 transition-colors duration-500
                                                ${file ? 'bg-blue-100 text-blue-600' : 'bg-slate-200 text-slate-500'}
                                            `}>
                                                {file ? <CheckCircle2 className="w-8 h-8" /> : <UploadCloud className="w-8 h-8" />}
                                            </div>
                                        </div>

                                        <h3 className="text-base font-semibold text-slate-900 mb-1">
                                            {file ? file.name : 'Sube PDF o Word'}
                                        </h3>
                                        <p className="text-xs text-slate-500">
                                            {file ? 'Listo para procesar' : 'Arrastra o haz clic'}
                                        </p>
                                    </div>
                                )}

                                {(!file) && (
                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 mb-2">O pega el texto aquí:</label>
                                        <textarea
                                            value={textInput}
                                            onChange={(e) => {
                                                setTextInput(e.target.value);
                                                setFile(null); // Clear file if typing
                                                setSlidesResult(false);
                                                setError(null);
                                            }}
                                            className="w-full h-32 p-4 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm leading-relaxed"
                                            placeholder="Introducción: El objetivo de este estudio..."
                                        />
                                    </div>
                                )}

                                <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                                    <div className="flex justify-between items-center mb-2">
                                        <label className="text-sm font-bold text-slate-700">Número de Diapositivas</label>
                                        <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs font-bold">{numSlides} Slides</span>
                                    </div>
                                    <input
                                        type="range"
                                        min="3"
                                        max="10"
                                        step="1"
                                        value={numSlides}
                                        onChange={(e) => setNumSlides(parseInt(e.target.value))}
                                        className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                                    />
                                    <div className="flex justify-between text-xs text-slate-400 mt-1">
                                        <span>3</span>
                                        <span>10</span>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div
                                className={`
                                    relative rounded-[20px] p-10 text-center transition-all duration-500 ease-out m-1
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
                                    accept=".pdf"
                                    onChange={handleFileChange}
                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                                />

                                <div className={`transition-transform duration-500 ${dragActive ? 'scale-110' : 'group-hover:scale-105'}`}>
                                    <div className={`
                                        w-24 h-24 mx-auto rounded-full flex items-center justify-center mb-6 transition-colors duration-500
                                        ${file ? 'bg-teal-100 text-teal-600' : 'bg-indigo-100 text-indigo-600'}
                                    `}>
                                        {file ? <CheckCircle2 className="w-12 h-12" /> : <UploadCloud className="w-12 h-12" />}
                                    </div>
                                </div>

                                <h3 className="text-xl font-semibold text-slate-900 mb-2">
                                    {file ? file.name : 'Sube tu Paper (PDF)'}
                                </h3>
                                <p className="text-sm text-slate-500 max-w-[250px] mx-auto">
                                    {file ? 'Listo para procesar' : 'Arrastra tu archivo aquí o haz clic para buscar'}
                                </p>
                            </div>
                        )}

                        {/* ACTION BUTTONS */}
                        <div className="p-6 grid grid-cols-1 gap-3">
                            <div className="grid grid-cols-2 gap-3">
                                <button
                                    onClick={() => handleGenerate('podcast')}
                                    disabled={loading || activeMode === 'slides'} // Disable if in slides mode to avoid confusion, or handle mode switch
                                    className={`
                                        py-3 rounded-xl font-bold text-white shadow-lg shadow-indigo-500/20
                                        flex items-center justify-center gap-2 transition-all duration-300 text-sm
                                        ${loading || activeMode === 'slides'
                                            ? 'bg-slate-200 text-slate-400 shadow-none'
                                            : 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:scale-[1.02]'
                                        }
                                    `}
                                >
                                    <Mic2 className="w-4 h-4" /> Podcast
                                </button>

                                <button
                                    onClick={() => handleGenerate('summary')}
                                    disabled={loading || activeMode === 'slides'}
                                    className={`
                                        py-3 rounded-xl font-bold text-white shadow-lg shadow-teal-500/20
                                        flex items-center justify-center gap-2 transition-all duration-300 text-sm
                                        ${loading || activeMode === 'slides'
                                            ? 'bg-slate-200 text-slate-400 shadow-none'
                                            : 'bg-gradient-to-r from-teal-500 to-emerald-600 hover:scale-[1.02]'
                                        }
                                    `}
                                >
                                    <FileText className="w-4 h-4" /> Resumen
                                </button>
                            </div>

                            {/* SLIDES BUTTON (Full Width) */}
                            <button
                                onClick={() => {
                                    if (activeMode !== 'slides') {
                                        setActiveMode('slides');
                                        setPodcastResult(null);
                                        setSummaryResult(null);
                                        setError(null);
                                    } else {
                                        handleGenerate('slides');
                                    }
                                }}
                                disabled={loading}
                                className={`
                                    w-full py-4 rounded-xl font-bold shadow-lg shadow-blue-500/20
                                    flex items-center justify-center gap-3 transition-all duration-300
                                    ${activeMode === 'slides'
                                        ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white hover:scale-[1.02]'
                                        : 'bg-white border-2 border-blue-100 text-blue-600 hover:bg-blue-50'}
                                `}
                            >
                                {loading && activeMode === 'slides' ? (
                                    <>
                                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        <span>Generando PPTX...</span>
                                    </>
                                ) : (
                                    <>
                                        <Presentation className="w-5 h-5" />
                                        <span>{activeMode === 'slides' ? 'Generar Presentación PPTX' : 'Cambiar a modo Slides'}</span>
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                            className="bg-red-50 border border-red-100 rounded-2xl p-4 flex items-center gap-3 text-red-700"
                        >
                            <AlertTriangle className="w-6 h-6 flex-shrink-0" />
                            <p>{error}</p>
                        </motion.div>
                    )}
                </div>

                {/* Right Column: Result */}
                <div className="lg:col-span-7">
                    <AnimatePresence mode="wait">
                        {!podcastResult && !summaryResult && !slidesResult && !loading && (
                            <motion.div
                                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                                className="h-full min-h-[400px] flex flex-col items-center justify-center text-slate-400 border-2 border-dashed border-slate-200 rounded-3xl bg-slate-50/50"
                            >
                                {activeMode === 'podcast' ? <Headphones className="w-20 h-20 mb-6 opacity-30" /> :
                                    activeMode === 'summary' ? <FileType className="w-20 h-20 mb-6 opacity-30" /> :
                                        <Presentation className="w-20 h-20 mb-6 opacity-30" />}
                                <p className="text-lg">El resultado aparecerá aquí</p>
                            </motion.div>
                        )}

                        {loading && (
                            <motion.div
                                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                                className="h-full min-h-[400px] flex flex-col items-center justify-center"
                            >
                                <div className="w-24 h-24 relative">
                                    <div className="absolute inset-0 border-4 border-slate-100 rounded-full"></div>
                                    <div className={`
                                        absolute inset-0 border-4 border-t-transparent rounded-full animate-spin
                                        ${activeMode === 'podcast' ? 'border-indigo-600' :
                                            activeMode === 'summary' ? 'border-teal-500' : 'border-blue-500'}
                                    `}></div>
                                </div>
                                <p className="mt-6 text-slate-600 font-medium animate-pulse">
                                    {activeMode === 'podcast' ? 'Sintetizando voces...' :
                                        activeMode === 'summary' ? 'Analizando contenido clave...' :
                                            'Diseñando diapositivas...'}
                                </p>
                            </motion.div>
                        )}

                        {/* PODCAST RESULT */}
                        {podcastResult && (
                            <motion.div
                                key="podcast-res"
                                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                                className="space-y-6"
                            >
                                {/* Audio Player Card */}
                                <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-3xl p-8 text-white shadow-2xl relative overflow-hidden">
                                    <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/20 rounded-full blur-3xl -mr-16 -mt-16"></div>

                                    <div className="relative z-10 flex flex-col items-center text-center">
                                        <div className="w-32 h-32 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mb-6 shadow-lg shadow-indigo-500/30">
                                            <button
                                                onClick={togglePlay}
                                                className="w-20 h-20 bg-white rounded-full flex items-center justify-center text-indigo-600 hover:scale-110 transition-transform"
                                            >
                                                {isPlaying ? <Pause className="w-8 h-8 fill-current" /> : <Play className="w-8 h-8 fill-current ml-1" />}
                                            </button>
                                        </div>

                                        <h3 className="text-2xl font-bold mb-2">{podcastResult.file_name}</h3>
                                        <p className="text-indigo-200 mb-6">Audio Abstract • Inphormed AI</p>

                                        <audio
                                            ref={audioRef}
                                            src={`data:audio/mp3;base64,${podcastResult.audio_base64}`}
                                            onEnded={() => setIsPlaying(false)}
                                            onPlay={() => setIsPlaying(true)}
                                            onPause={() => setIsPlaying(false)}
                                            controls
                                            className="w-full opacity-80 hover:opacity-100 transition-opacity"
                                        />
                                    </div>
                                </div>

                                {/* Transcript */}
                                <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
                                    <div className="p-4 border-b border-slate-100 bg-slate-50/50">
                                        <h4 className="font-bold text-slate-700 flex items-center gap-2">
                                            <FileText className="w-4 h-4" /> Transcripción
                                        </h4>
                                    </div>
                                    <div className="p-6 space-y-6 max-h-[500px] overflow-y-auto custom-scrollbar">
                                        {podcastResult.script.map((turn, idx) => (
                                            <div key={idx} className={`flex gap-4 ${turn.speaker === 'Host' ? '' : 'flex-row-reverse'}`}>
                                                <div className={`
                                                    w-10 h-10 rounded-full flex-shrink-0 flex items-center justify-center font-bold text-sm shadow-sm
                                                    ${turn.speaker === 'Host' ? 'bg-indigo-100 text-indigo-700' : 'bg-teal-100 text-teal-700'}
                                                `}>
                                                    {turn.speaker === 'Host' ? 'H' : 'E'}
                                                </div>
                                                <div className={`
                                                    p-4 rounded-2xl max-w-[80%] text-sm leading-relaxed shadow-sm
                                                    ${turn.speaker === 'Host'
                                                        ? 'bg-white border border-slate-100 text-slate-700 rounded-tl-none'
                                                        : 'bg-slate-50 border border-slate-100 text-slate-800 rounded-tr-none'}
                                                `}>
                                                    <p className="font-bold text-xs mb-1 opacity-50 uppercase tracking-wider">{turn.speaker}</p>
                                                    {turn.text}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </motion.div>
                        )}

                        {/* SUMMARY RESULT */}
                        {summaryResult && (
                            <motion.div
                                key="summary-res"
                                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                                className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden"
                            >
                                <div className="p-6 border-b border-slate-100 bg-teal-50/30 flex justify-between items-center">
                                    <h3 className="text-xl font-bold text-slate-800">Resumen Ejecutivo</h3>
                                    <span className="text-sm text-slate-500 font-mono bg-white px-2 py-1 rounded border">
                                        {summaryResult.file_name}
                                    </span>
                                </div>
                                <div className="p-8 prose prose-slate max-w-none">
                                    <div className="whitespace-pre-wrap text-slate-700 leading-relaxed">
                                        {summaryResult.summary}
                                    </div>
                                </div>
                            </motion.div>
                        )}

                        {/* SLIDES RESULT */}
                        {slidesResult && (
                            <motion.div
                                key="slides-res"
                                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                                className="h-full min-h-[400px] flex flex-col items-center justify-center bg-blue-50/50 rounded-3xl border border-blue-100"
                            >
                                <div className="w-24 h-24 bg-blue-100 rounded-full flex items-center justify-center mb-6 text-blue-600">
                                    <CheckCircle2 className="w-12 h-12" />
                                </div>
                                <h3 className="text-2xl font-bold text-slate-800 mb-2">¡Presentación Lista!</h3>
                                <p className="text-slate-600 mb-8">Tu archivo PowerPoint se ha descargado automáticamente.</p>

                                <button
                                    onClick={() => handleGenerate('slides')}
                                    className="px-8 py-3 bg-white text-blue-600 font-bold rounded-xl shadow-sm border border-blue-200 hover:bg-blue-50 flex items-center gap-2"
                                >
                                    <Download className="w-5 h-5" />
                                    Generar de nuevo
                                </button>
                            </motion.div>
                        )}

                    </AnimatePresence>
                </div>
            </div>

            <FloatingChat context="generator" />
        </div>
    );
}
