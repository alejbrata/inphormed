'use client';

import { useState, useRef, useEffect } from 'react';
import FloatingChat from './FloatingChat';
import { motion, AnimatePresence } from 'framer-motion';
import { UploadCloud, FileText, Play, Pause, Mic2, Sparkles, CheckCircle2, AlertTriangle, Headphones, FileType, Presentation, Download, ShieldAlert, Stethoscope } from 'lucide-react';
import { generatePodcast, generateSummary, generateSlides, generateBattleCard, generateMedInfo, type PodcastResponse, type SummaryResponse, type BattleCardAnalysis, type MedInfoResponse } from '@/lib/api';

export default function MaterialGenerator() {
    const [activeMode, setActiveMode] = useState<'podcast' | 'summary' | 'slides' | 'battle-card' | 'medinfo'>('podcast');
    const [file, setFile] = useState<File | null>(null);
    const [textInput, setTextInput] = useState(''); // For slides
    const [numSlides, setNumSlides] = useState(5); // Default 5 slides
    const [isOnePager, setIsOnePager] = useState(false); // New One-Pager State
    const [loading, setLoading] = useState(false);

    // Results
    const [podcastResult, setPodcastResult] = useState<PodcastResponse | null>(null);
    const [summaryResult, setSummaryResult] = useState<SummaryResponse | null>(null);
    const [slidesResult, setSlidesResult] = useState<boolean>(false); // Just to show success state
    const [battleCardResult, setBattleCardResult] = useState<BattleCardAnalysis | null>(null);
    const [medInfoResult, setMedInfoResult] = useState<MedInfoResponse | null>(null);

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
        setBattleCardResult(null);
        setMedInfoResult(null);
        setError(null);
        setIsPlaying(false);
    };

    const handleGenerate = async (mode: 'podcast' | 'summary' | 'slides' | 'battle-card' | 'medinfo') => {
        if (mode !== 'slides' && !file) return;
        if (mode === 'slides' && !textInput.trim() && !file) {
            setError("Por favor, introduce texto o sube un archivo.");
            return;
        }

        setLoading(true);
        setActiveMode(mode);
        setError(null);
        resetResults();

        try {
            if (mode === 'podcast' && file) {
                const data = await generatePodcast(file);
                setPodcastResult(data);
            } else if (mode === 'summary' && file) {
                const data = await generateSummary(file);
                setSummaryResult(data);
            } else if (mode === 'slides') {
                const style = isOnePager ? 'one_pager' : 'default';
                const slidesCount = isOnePager ? 1 : numSlides;
                const blob = await generateSlides(textInput, file, slidesCount, style);

                // Trigger download
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = isOnePager ? 'executive_one_pager.pdf' : 'generated_presentation.pptx';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                setSlidesResult(true);
            } else if (mode === 'battle-card' && file) {
                const data = await generateBattleCard(file);
                setBattleCardResult(data);
            } else if (mode === 'medinfo' && file) {
                const data = await generateMedInfo(file);
                setMedInfoResult(data);
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
            {/* INPUT SECTION */}
            {!podcastResult && !summaryResult && !slidesResult && !battleCardResult && !medInfoResult && (
                <div className="space-y-8">
                    {/* Header */}
                    <div className="text-center space-y-4">
                        <h2 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-teal-500">
                            Generador de Materiales
                        </h2>
                        <p className="text-slate-500 max-w-2xl mx-auto text-lg">
                            Transforma papers clínicos en contenido de alto valor: podcasts, resúmenes, presentaciones y análisis estratégicos.
                        </p>
                    </div>

                    {/* Mode Selector */}
                    <div className="flex flex-wrap justify-center gap-4">
                        <button
                            onClick={() => setActiveMode('podcast')}
                            className={`px-6 py-3 rounded-2xl font-bold transition-all flex items-center gap-2 ${activeMode === 'podcast' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-200 scale-105' : 'bg-white text-slate-600 hover:bg-slate-50'}`}
                        >
                            <Headphones className="w-5 h-5" /> Audio Podcast
                        </button>
                        <button
                            onClick={() => setActiveMode('summary')}
                            className={`px-6 py-3 rounded-2xl font-bold transition-all flex items-center gap-2 ${activeMode === 'summary' ? 'bg-teal-600 text-white shadow-lg shadow-teal-200 scale-105' : 'bg-white text-slate-600 hover:bg-slate-50'}`}
                        >
                            <FileText className="w-5 h-5" /> Resumen Ejecutivo
                        </button>
                        <button
                            onClick={() => setActiveMode('slides')}
                            className={`px-6 py-3 rounded-2xl font-bold transition-all flex items-center gap-2 ${activeMode === 'slides' ? 'bg-blue-600 text-white shadow-lg shadow-blue-200 scale-105' : 'bg-white text-slate-600 hover:bg-slate-50'}`}
                        >
                            <Presentation className="w-5 h-5" /> Presentación PPT
                        </button>
                        <button
                            onClick={() => setActiveMode('battle-card')}
                            className={`px-6 py-3 rounded-2xl font-bold transition-all flex items-center gap-2 ${activeMode === 'battle-card' ? 'bg-orange-600 text-white shadow-lg shadow-orange-200 scale-105' : 'bg-white text-slate-600 hover:bg-slate-50'}`}
                        >
                            <ShieldAlert className="w-5 h-5" /> Battle Card
                        </button>
                        <button
                            onClick={() => setActiveMode('medinfo')}
                            className={`px-6 py-3 rounded-2xl font-bold transition-all flex items-center gap-2 ${activeMode === 'medinfo' ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-200 scale-105' : 'bg-white text-slate-600 hover:bg-slate-50'}`}
                        >
                            <Stethoscope className="w-5 h-5" /> MedInfo
                        </button>
                    </div>

                    {/* Upload Area */}
                    <div
                        onDragOver={handleDrag}
                        onDragLeave={handleDrag}
                        onDrop={handleDrop}
                        className={`
                            relative border-3 border-dashed rounded-3xl p-12 text-center transition-all duration-300 group
                            ${file ? 'border-teal-500 bg-teal-50/30' : 'border-slate-200 hover:border-indigo-400 hover:bg-slate-50'}
                        `}
                    >
                        <input
                            type="file"
                            onChange={handleFileChange}
                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                            accept=".pdf"
                        />

                        <div className="flex flex-col items-center gap-4 pointer-events-none">
                            <div className={`
                                w-20 h-20 rounded-full flex items-center justify-center transition-colors
                                ${file ? 'bg-teal-100 text-teal-600' : 'bg-indigo-50 text-indigo-500 group-hover:bg-indigo-100 group-hover:text-indigo-600'}
                            `}>
                                {file ? <CheckCircle2 className="w-10 h-10" /> : <UploadCloud className="w-10 h-10" />}
                            </div>

                            <div>
                                <h3 className="text-xl font-bold text-slate-700 mb-2">
                                    {file ? file.name : 'Arrastra tu paper clínico aquí'}
                                </h3>
                                <p className="text-slate-400">
                                    {file ? 'Archivo listo para procesar' : 'O haz clic para explorar tus archivos (PDF)'}
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Configuration Area (Slides Only) */}
                    {activeMode === 'slides' && (
                        <div className="flex flex-col items-center gap-4 animate-fade-in">
                            <div className="flex items-center gap-4 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
                                <label className="flex items-center gap-3 cursor-pointer">
                                    <div className="relative">
                                        <input
                                            type="checkbox"
                                            className="sr-only peer"
                                            checked={isOnePager}
                                            onChange={(e) => setIsOnePager(e.target.checked)}
                                        />
                                        <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                                    </div>
                                    <span className="text-sm font-medium text-slate-700">
                                        Generar como <span className="font-bold text-blue-600">Executive One-Pager</span> (Resumen Visual)
                                    </span>
                                </label>
                            </div>

                            {!isOnePager && (
                                <div className="flex items-center gap-3 bg-white px-4 py-2 rounded-xl border border-slate-200">
                                    <span className="text-sm text-slate-500 font-medium">Diapositivas:</span>
                                    <input
                                        type="number"
                                        min="3"
                                        max="20"
                                        value={numSlides}
                                        onChange={(e) => setNumSlides(parseInt(e.target.value))}
                                        className="w-16 p-1 text-center border rounded-lg font-bold text-slate-700 focus:ring-2 focus:ring-blue-500 outline-none"
                                    />
                                </div>
                            )}
                        </div>
                    )}

                    {/* Generate Button */}
                    <div className="flex justify-center">
                        <button
                            onClick={() => handleGenerate(activeMode)}
                            disabled={!file || loading}
                            className={`
                                px-10 py-4 rounded-2xl font-bold text-lg shadow-xl hover:shadow-2xl transition-all flex items-center gap-3
                                ${!file || loading
                                    ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                                    : activeMode === 'battle-card' ? 'bg-gradient-to-r from-orange-600 to-red-600 text-white hover:scale-105'
                                        : activeMode === 'medinfo' ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white hover:scale-105'
                                            : 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:scale-105'}
                            `}
                        >
                            {loading ? (
                                <>
                                    <div className="w-6 h-6 border-3 border-white/30 border-t-white rounded-full animate-spin" />
                                    {activeMode === 'battle-card' ? 'Detectando debilidades...' :
                                        activeMode === 'medinfo' ? 'Redactando respuesta...' :
                                            'Generando contenido...'}
                                </>
                            ) : (
                                <>
                                    <Sparkles className="w-6 h-6" />
                                    Generar {activeMode === 'podcast' ? 'Podcast' : activeMode === 'summary' ? 'Resumen' : activeMode === 'slides' ? 'Presentación' : activeMode === 'battle-card' ? 'Battle Card' : 'Respuesta'}
                                </>
                            )}
                        </button>
                    </div>
                </div>
            )}

            <AnimatePresence mode="wait">
                {/* Header */}
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

                        {/* Audio Player for Summary */}
                        {summaryResult.audio_base64 && (
                            <div className="bg-slate-900 p-6 text-white flex items-center gap-6">
                                <button
                                    onClick={() => {
                                        if (audioRef.current) {
                                            if (isPlaying) audioRef.current.pause();
                                            else audioRef.current.play();
                                            setIsPlaying(!isPlaying);
                                        }
                                    }}
                                    className="w-14 h-14 bg-teal-500 rounded-full flex items-center justify-center hover:scale-105 transition-transform shadow-lg shadow-teal-500/30 flex-shrink-0"
                                >
                                    {isPlaying ? <Pause className="w-6 h-6 fill-current" /> : <Play className="w-6 h-6 fill-current ml-1" />}
                                </button>

                                <div className="flex-1">
                                    <h4 className="font-bold text-lg mb-1">Escuchar Resumen</h4>
                                    <p className="text-slate-400 text-sm">Audio generado por IA • Inphormed</p>
                                </div>

                                <audio
                                    ref={audioRef}
                                    src={`data:audio/mp3;base64,${summaryResult.audio_base64}`}
                                    onEnded={() => setIsPlaying(false)}
                                    onPlay={() => setIsPlaying(true)}
                                    onPause={() => setIsPlaying(false)}
                                    className="hidden"
                                />
                            </div>
                        )}

                        <div className="p-8 prose prose-slate max-w-none">
                            <div className="whitespace-pre-wrap text-slate-700 leading-relaxed">
                                {summaryResult.summary}
                            </div>
                        </div>
                    </motion.div>
                )}

                {/* BATTLE CARD RESULT */}
                {battleCardResult && (
                    <motion.div
                        key="battle-card-res"
                        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                        className="space-y-6"
                    >
                        {/* Threat Level Card */}
                        <div className={`
                                    rounded-3xl p-8 text-white shadow-xl relative overflow-hidden
                                    ${battleCardResult.overall_threat_level === 'Alto' ? 'bg-gradient-to-br from-red-600 to-orange-700' :
                                battleCardResult.overall_threat_level === 'Medio' ? 'bg-gradient-to-br from-amber-500 to-orange-600' :
                                    'bg-gradient-to-br from-emerald-500 to-teal-600'}
                                `}>
                            <div className="relative z-10 flex flex-col items-center text-center">
                                <ShieldAlert className="w-16 h-16 mb-4 opacity-90" />
                                <h3 className="text-3xl font-bold mb-2">Nivel de Amenaza: {battleCardResult.overall_threat_level}</h3>
                                <p className="opacity-80">Análisis de Competencia</p>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Design Flaws */}
                            <div className="bg-white rounded-3xl border border-red-100 shadow-sm p-6">
                                <h4 className="font-bold text-red-700 flex items-center gap-2 mb-4">
                                    <AlertTriangle className="w-5 h-5" /> Debilidades de Diseño
                                </h4>
                                <ul className="space-y-3">
                                    {battleCardResult.study_design_flaws.map((flaw, idx) => (
                                        <li key={idx} className="flex gap-3 text-sm text-slate-700">
                                            <span className="text-red-400 font-bold">•</span>
                                            {flaw}
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            {/* Safety Signals */}
                            <div className="bg-white rounded-3xl border border-orange-100 shadow-sm p-6">
                                <h4 className="font-bold text-orange-700 flex items-center gap-2 mb-4">
                                    <AlertTriangle className="w-5 h-5" /> Señales de Seguridad
                                </h4>
                                <ul className="space-y-3">
                                    {battleCardResult.safety_signals.map((signal, idx) => (
                                        <li key={idx} className="flex gap-3 text-sm text-slate-700">
                                            <span className="text-orange-400 font-bold">•</span>
                                            {signal}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        {/* Counter Arguments */}
                        <div className="bg-slate-900 rounded-3xl p-8 text-slate-300 shadow-lg">
                            <h4 className="font-bold text-white flex items-center gap-2 mb-6">
                                <Sparkles className="w-5 h-5 text-yellow-400" /> Argumentos Estratégicos
                            </h4>
                            <div className="grid gap-4">
                                {battleCardResult.strategic_counter_arguments.map((arg, idx) => (
                                    <div key={idx} className="bg-slate-800/50 p-4 rounded-xl border border-slate-700">
                                        <p className="font-medium text-white">"{arg}"</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </motion.div>
                )}

                {/* MEDINFO RESULT */}
                {medInfoResult && (
                    <motion.div
                        key="medinfo-res"
                        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                        className="space-y-6"
                    >
                        {/* Header Card */}
                        <div className="bg-gradient-to-br from-cyan-600 to-blue-700 rounded-3xl p-8 text-white shadow-xl relative overflow-hidden">
                            <div className="relative z-10 flex flex-col items-center text-center">
                                <Stethoscope className="w-16 h-16 mb-4 opacity-90" />
                                <h3 className="text-2xl font-bold mb-2">Carta de Respuesta Estándar</h3>
                                <p className="opacity-80 font-mono text-sm bg-white/20 px-3 py-1 rounded-full">
                                    {medInfoResult.subject}
                                </p>
                            </div>
                        </div>

                        {/* Summary Section */}
                        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-8">
                            <h4 className="font-bold text-slate-800 flex items-center gap-2 mb-4 text-lg">
                                <FileText className="w-5 h-5 text-cyan-600" /> Resumen Ejecutivo
                            </h4>
                            <p className="text-slate-600 leading-relaxed text-justify">
                                {medInfoResult.summary}
                            </p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Efficacy Data */}
                            <div className="bg-white rounded-3xl border border-cyan-100 shadow-sm p-6">
                                <h4 className="font-bold text-cyan-700 flex items-center gap-2 mb-4">
                                    <CheckCircle2 className="w-5 h-5" /> Datos de Eficacia
                                </h4>
                                <ul className="space-y-3">
                                    {medInfoResult.efficacy_data.map((item, idx) => (
                                        <li key={idx} className="flex gap-3 text-sm text-slate-700">
                                            <span className="text-cyan-400 font-bold">•</span>
                                            {item}
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            {/* Safety Data */}
                            <div className="bg-white rounded-3xl border border-blue-100 shadow-sm p-6">
                                <h4 className="font-bold text-blue-700 flex items-center gap-2 mb-4">
                                    <ShieldAlert className="w-5 h-5" /> Datos de Seguridad
                                </h4>
                                <ul className="space-y-3">
                                    {medInfoResult.safety_data.map((item, idx) => (
                                        <li key={idx} className="flex gap-3 text-sm text-slate-700">
                                            <span className="text-blue-400 font-bold">•</span>
                                            {item}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        {/* Limitations & References */}
                        <div className="grid grid-cols-1 gap-6">
                            <div className="bg-slate-50 rounded-3xl border border-slate-200 p-6">
                                <h4 className="font-bold text-slate-700 flex items-center gap-2 mb-4">
                                    <AlertTriangle className="w-5 h-5 text-amber-500" /> Limitaciones del Estudio
                                </h4>
                                <ul className="space-y-2">
                                    {medInfoResult.limitations.map((lim, idx) => (
                                        <li key={idx} className="text-sm text-slate-600 italic flex gap-2">
                                            <span>-</span> {lim}
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            <div className="bg-slate-900 rounded-3xl p-6 text-slate-400 text-xs">
                                <h4 className="font-bold text-white mb-3 uppercase tracking-wider">Referencias Bibliográficas</h4>
                                <ul className="space-y-2">
                                    {medInfoResult.references.map((ref, idx) => (
                                        <li key={idx}>{ref}</li>
                                    ))}
                                </ul>
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
                        <p className="text-slate-600 mb-8">Tu archivo {isOnePager ? 'PDF' : 'PowerPoint'} se ha descargado automáticamente.</p>

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

            <FloatingChat context="generator" />
        </div>
    );
}
