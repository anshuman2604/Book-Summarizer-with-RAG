'use client';

import React, { useState, useEffect, useRef } from 'react';
import { api } from '@/lib/api';
import { 
  BookOpen, 
  Upload, 
  Send, 
  LogOut, 
  FileText, 
  Sparkles, 
  Trash2, 
  Clock, 
  CheckCircle2, 
  AlertCircle,
  HelpCircle,
  Loader2
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

interface Book {
  id: string;
  title: string;
  filename: string;
  file_type: string;
  total_pages: number;
  summary_100_words: string | null;
  created_at: string;
}

interface Source {
  page_number: number | null;
  snippet: string;
}

interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
}

export default function Dashboard() {
  const [token, setToken] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string>('');

  // Auth form states
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authError, setAuthError] = useState('');

  // App data states
  const [books, setBooks] = useState<Book[]>([]);
  const [selectedBook, setSelectedBook] = useState<Book | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState('');

  // Loading states
  const [isUploading, setIsUploading] = useState(false);
  const [uploadFileName, setUploadFileName] = useState('');
  const [uploadStage, setUploadStage] = useState('Extracting pages & text...');
  const [isAsking, setIsAsking] = useState(false);
  const [uploadError, setUploadError] = useState('');

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Initialize token from localStorage
  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    const storedEmail = localStorage.getItem('userEmail');
    if (storedToken) {
      setToken(storedToken);
      setUserEmail(storedEmail || '');
    }
  }, []);

  // Fetch books history whenever token changes
  useEffect(() => {
    if (token) {
      fetchBooks();
    } else {
      setBooks([]);
      setSelectedBook(null);
      setChatMessages([]);
    }
  }, [token]);

  // Scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const fetchBooks = async () => {
    try {
      const res = await api.get('/books');
      setBooks(res.data.books);
      if (res.data.books.length > 0 && !selectedBook) {
        selectBook(res.data.books[0]);
      }
    } catch (err) {
      console.error('Failed to fetch books', err);
    }
  };

  const selectBook = async (book: Book) => {
    setSelectedBook(book);
    try {
      const res = await api.get(`/books/${book.id}/chat/history`);
      setChatMessages(res.data);
    } catch (err) {
      console.error('Failed to fetch chat history', err);
    }
  };

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    try {
      if (authMode === 'register') {
        await api.post('/auth/register', {
          email: authEmail,
          password: authPassword,
        });
      }
      const res = await api.post('/auth/login', {
        email: authEmail,
        password: authPassword,
      });
      localStorage.setItem('token', res.data.access_token);
      localStorage.setItem('userEmail', res.data.email);
      setToken(res.data.access_token);
      setUserEmail(res.data.email);
      setAuthPassword('');
    } catch (err: any) {
      setAuthError(err.response?.data?.detail || 'Authentication failed. Please check credentials.');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('userEmail');
    setToken(null);
    setUserEmail('');
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadFileName(file.name);
    setIsUploading(true);
    setUploadError('');
    setUploadStage('Extracting text & page structures...');

    // Progress through visual stages to keep user engaged during 500-page processing
    const timer1 = setTimeout(() => {
      setUploadStage('Generating 100-word executive summary with Gemini...');
    }, 2500);

    const timer2 = setTimeout(() => {
      setUploadStage('Embedding semantic chunks into Supabase pgvector...');
    }, 5500);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post('/books/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const newBook = res.data;
      setBooks((prev) => [newBook, ...prev]);
      setSelectedBook(newBook);
      setChatMessages([]);
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'Upload failed. Please ensure file is a valid PDF or DOCX.');
    } finally {
      clearTimeout(timer1);
      clearTimeout(timer2);
      setIsUploading(false);
      e.target.value = '';
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || !selectedBook || isAsking) return;

    const userQ = question.trim();
    setQuestion('');
    setChatMessages((prev) => [...prev, { role: 'user', content: userQ }]);
    setIsAsking(true);

    try {
      const res = await api.post(`/books/${selectedBook.id}/chat`, {
        question: userQ,
      });
      setChatMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: res.data.answer,
          sources: res.data.sources,
        },
      ]);
    } catch (err: any) {
      setChatMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error while searching for answers in this book.',
        },
      ]);
    } finally {
      setIsAsking(false);
    }
  };

  const handleDeleteBook = async (bookId: string) => {
    if (!confirm('Are you sure you want to delete this book and its history?')) return;
    try {
      await api.delete(`/books/${bookId}`);
      setBooks((prev) => prev.filter((b) => b.id !== bookId));
      if (selectedBook?.id === bookId) {
        setSelectedBook(books.find((b) => b.id !== bookId) || null);
        setChatMessages([]);
      }
    } catch (err) {
      alert('Failed to delete book');
    }
  };

  // Auth Screen if not logged in
  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4">
        <div className="bg-slate-800 border border-slate-700 p-8 rounded-2xl shadow-2xl w-full max-w-md text-slate-100">
          <div className="flex items-center gap-3 mb-6 justify-center">
            <div className="p-3 bg-blue-600 rounded-xl">
              <BookOpen className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">BookAI Agent</h1>
              <p className="text-xs text-slate-400">100-Word Summarizer & RAG</p>
            </div>
          </div>

          <div className="flex rounded-lg bg-slate-700/50 p-1 mb-6">
            <button
              onClick={() => { setAuthMode('login'); setAuthError(''); }}
              className={`flex-1 py-2 text-sm font-medium rounded-md transition ${
                authMode === 'login' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => { setAuthMode('register'); setAuthError(''); }}
              className={`flex-1 py-2 text-sm font-medium rounded-md transition ${
                authMode === 'register' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              Register
            </button>
          </div>

          {authError && (
            <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm mb-4">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <p>{authError}</p>
            </div>
          )}

          <form onSubmit={handleAuth} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Email Address</label>
              <input
                type="email"
                required
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                className="w-full px-4 py-2.5 bg-slate-900/80 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Password</label>
              <input
                type="password"
                required
                minLength={6}
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                className="w-full px-4 py-2.5 bg-slate-900/80 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="•••••••• (min 6 characters)"
              />
            </div>
            <button
              type="submit"
              className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg text-sm transition shadow-lg shadow-blue-600/30"
            >
              {authMode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // Main Dashboard
  return (
    <div className="relative flex h-screen bg-slate-900 text-slate-100 overflow-hidden font-sans">
      {/* Full-Screen Uploading & Processing Modal Overlay */}
      {isUploading && (
        <div className="absolute inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-700/80 p-8 rounded-3xl shadow-2xl max-w-md w-full flex flex-col items-center">
            {/* Animated Glow Spinner */}
            <div className="relative mb-6">
              <div className="w-16 h-16 rounded-full border-4 border-blue-500/20 border-t-blue-500 animate-spin" />
              <Sparkles className="w-7 h-7 text-blue-400 absolute inset-0 m-auto animate-pulse" />
            </div>

            <h3 className="text-lg font-bold text-white mb-1.5">Processing Book</h3>
            <p className="text-sm font-medium text-blue-400 truncate max-w-xs mb-4">
              "{uploadFileName || 'Document'}"
            </p>

            {/* Dynamic Stage Banner */}
            <div className="w-full bg-slate-800/80 border border-slate-700/50 rounded-xl p-3.5 mb-5 flex items-center justify-center gap-2.5 text-slate-200 text-xs">
              <Loader2 className="w-4 h-4 text-blue-400 animate-spin shrink-0" />
              <span>{uploadStage}</span>
            </div>

            {/* Step Indicators */}
            <div className="w-full space-y-2 text-left text-xs text-slate-400">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span>Page-by-page text extraction</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3.5 h-3.5 rounded-full border border-blue-400/40 bg-blue-500/20 flex items-center justify-center">
                  <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-ping" />
                </div>
                <span>Synthesizing strict 100-word executive summary</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3.5 h-3.5 rounded-full border border-slate-600 shrink-0" />
                <span>Cohere vector indexing into Supabase pgvector</span>
              </div>
            </div>

            <p className="text-[11px] text-slate-400 mt-6 italic">
              Large books (500+ pages) typically complete in ~15 to 20 seconds.
            </p>
          </div>
        </div>
      )}

      {/* Sidebar: Books History & Upload */}
      <div className="w-80 bg-slate-950 border-r border-slate-800 flex flex-col shrink-0">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="p-2 bg-blue-600/20 text-blue-400 rounded-lg shrink-0">
              <BookOpen className="w-5 h-5" />
            </div>
            <div className="overflow-hidden">
              <h2 className="text-sm font-bold truncate">BookAI Agent</h2>
              <p className="text-xs text-slate-400 truncate">{userEmail}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            title="Logout"
            className="p-2 text-slate-400 hover:text-red-400 hover:bg-slate-900 rounded-lg transition"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>

        {/* Upload Button */}
        <div className="p-4 border-b border-slate-800">
          <label className="flex items-center justify-center gap-2 w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium cursor-pointer transition shadow-lg shadow-blue-600/20">
            <Upload className="w-4 h-4" />
            <span>{isUploading ? 'Ingesting & Summarizing...' : 'Upload Book (PDF/DOCX)'}</span>
            <input
              type="file"
              accept=".pdf,.docx,.doc"
              onChange={handleFileUpload}
              disabled={isUploading}
              className="hidden"
            />
          </label>
          {uploadError && (
            <p className="text-xs text-red-400 mt-2">{uploadError}</p>
          )}
        </div>

        {/* Book History List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          <p className="text-xs font-semibold text-slate-400 px-3 py-2 uppercase tracking-wider">
            Your Books History ({books.length})
          </p>
          {books.length === 0 ? (
            <div className="text-center py-10 px-4 text-slate-400">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-xs">No books uploaded yet. Upload a 500+ page book to start!</p>
            </div>
          ) : (
            books.map((b) => (
              <div
                key={b.id}
                onClick={() => selectBook(b)}
                className={`group flex items-center justify-between p-3 rounded-lg cursor-pointer transition border ${
                  selectedBook?.id === b.id
                    ? 'bg-blue-600/10 border-blue-500/30 text-white'
                    : 'border-transparent text-slate-400 hover:bg-slate-900 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center gap-2.5 overflow-hidden">
                  <FileText className={`w-4 h-4 shrink-0 ${selectedBook?.id === b.id ? 'text-blue-400' : 'text-slate-400'}`} />
                  <div className="overflow-hidden">
                    <p className="text-sm font-medium truncate">{b.title}</p>
                    <p className={`text-xs truncate ${selectedBook?.id === b.id ? 'text-blue-400' : 'text-slate-400'}`}>
                      {b.total_pages} pages • {b.file_type.toUpperCase()}
                    </p>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteBook(b.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 hover:text-red-400 transition"
                  title="Delete Book"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Content Area */}
      {selectedBook ? (
        <div className="flex-1 flex flex-col h-full bg-slate-900 overflow-hidden">
          {/* Top Bar: Book Metadata */}
          <div className="p-4 border-b border-slate-800 bg-slate-950/60 backdrop-blur flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">{selectedBook.title}</h2>
              <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                <span>{selectedBook.total_pages} Pages</span>
                <span>•</span>
                <span>Format: {selectedBook.file_type.toUpperCase()}</span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {new Date(selectedBook.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium rounded-full">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>pgvector Indexed</span>
            </div>
          </div>

          {/* Center Area: Split between 100-Word Summary and Q&A Chat */}
          <div className="flex-1 flex overflow-hidden">
            {/* Left Box: 100-Word Summary Card */}
            <div className="w-1/3 border-r border-slate-800 p-6 overflow-y-auto flex flex-col bg-slate-900/50">
              <div className="flex items-center gap-2 mb-3 text-blue-400">
                <Sparkles className="w-5 h-5" />
                <h3 className="font-bold text-sm tracking-wide uppercase">100-Word Executive Summary</h3>
              </div>
              <div className="p-5 bg-slate-800 border border-slate-700 rounded-2xl shadow-inner text-slate-200 text-sm leading-relaxed space-y-3">
                <p className="italic text-slate-300">
                  "{selectedBook.summary_100_words || 'Summary was not generated for this book.'}"
                </p>
              </div>
              <div className="mt-4 text-xs text-slate-400 flex items-center gap-1.5">
                <HelpCircle className="w-3.5 h-3.5" />
                <span>Generated via LangChain Map-Reduce over 6 macro-sections.</span>
              </div>
            </div>

            {/* Right Box: RAG Q&A Chat */}
            <div className="flex-1 flex flex-col h-full bg-slate-900">
              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {chatMessages.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center text-slate-400 max-w-sm mx-auto">
                    <div className="p-4 bg-slate-800/60 rounded-full mb-3">
                      <HelpCircle className="w-8 h-8 text-blue-400" />
                    </div>
                    <h4 className="text-base font-semibold text-white mb-1">Ask questions about this book</h4>
                    <p className="text-xs text-slate-400">
                      Our Agent searches PostgreSQL pgvector embeddings and cites exact page numbers.
                    </p>
                  </div>
                ) : (
                  chatMessages.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
                    >
                      <div
                        className={`max-w-2xl px-5 py-3.5 rounded-2xl text-sm leading-relaxed ${
                          msg.role === 'user'
                            ? 'bg-blue-600 text-white rounded-br-none shadow-md shadow-blue-600/20'
                            : 'bg-slate-800 border border-slate-700 text-slate-200 rounded-bl-none shadow-sm markdown-body'
                        }`}
                      >
                        {msg.role === 'user' ? (
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                        ) : (
                          <div className="space-y-2 [&_p]:mb-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_h3]:font-bold [&_h3]:text-base [&_h3]:mt-3 [&_h3]:mb-1 [&_h2]:font-bold [&_h2]:text-lg [&_h2]:mt-4 [&_h2]:mb-2 [&_hr]:my-3 [&_hr]:border-slate-700 [&_.katex-display]:my-3 [&_.katex-display]:overflow-x-auto [&_.katex-display]:py-1">
                            <ReactMarkdown
                              remarkPlugins={[remarkMath]}
                              rehypePlugins={[rehypeKatex]}
                            >
                              {msg.content}
                            </ReactMarkdown>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
                {isAsking && (
                  <div className="flex items-start">
                    <div className="px-5 py-3.5 bg-slate-800 border border-slate-700 rounded-2xl rounded-bl-none text-slate-400 text-sm flex items-center gap-2">
                      <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
                      <span>Agent retrieving vector embeddings & citing pages...</span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Chat Input Bar */}
              <div className="p-4 border-t border-slate-800 bg-slate-950/40">
                <form onSubmit={handleSendMessage} className="flex gap-2 max-w-4xl mx-auto">
                  <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder={`Ask any question about "${selectedBook.title}" (answers include page citations)...`}
                    disabled={isAsking}
                    className="flex-1 px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    type="submit"
                    disabled={!question.trim() || isAsking}
                    className="px-5 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl transition flex items-center gap-2 shadow-lg shadow-blue-600/30 font-medium text-sm"
                  >
                    <Send className="w-4 h-4" />
                    <span>Ask Agent</span>
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400">
          <BookOpen className="w-12 h-12 text-slate-400 mb-3 opacity-40" />
          <h3 className="text-lg font-semibold text-white mb-1">No Book Selected</h3>
          <p className="text-sm max-w-sm">
            Select a book from the history sidebar or upload a new PDF or DOCX file to get started.
          </p>
        </div>
      )}
    </div>
  );
}
