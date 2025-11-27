import React from 'react';
import Link from 'next/link';

export default function Home() {
    return (
        <main className="flex min-h-screen flex-col items-center justify-center p-24 bg-gray-100">
            <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm lg:flex flex-col">
                <h1 className="text-4xl font-bold text-blue-800 mb-8">
                    Bem-vindo ao Dashboard de Lucratividade SaaS
                </h1>

                <p className="text-lg text-gray-700 mb-8 text-center max-w-2xl">
                    Gerencie suas vendas, calcule impostos reais e otimize sua logística em um só lugar.
                </p>

                <Link href="/login">
                    <button className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg shadow-lg transition duration-300">
                        Login
                    </button>
                </Link>
            </div>
        </main>
    );
}
