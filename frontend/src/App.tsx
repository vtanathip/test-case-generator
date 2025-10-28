import React from 'react'
import { Routes, Route } from 'react-router-dom'

// Basic App component for the Test Case Generator
const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">
            Test Case Generator
          </h1>
        </div>
      </header>
      
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/about" element={<About />} />
        </Routes>
      </main>
    </div>
  )
}

// Dashboard component
const Dashboard: React.FC = () => {
  return (
    <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0">
        <div className="border-4 border-dashed border-gray-200 rounded-lg h-96 flex items-center justify-center">
          <div className="text-center">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              Welcome to Test Case Generator
            </h2>
            <p className="text-gray-600 mb-4">
              AI-powered test case generation for your GitHub repositories.
            </p>
            <div className="space-y-2 text-sm text-gray-500">
              <p>• Connect your GitHub repository</p>
              <p>• AI analyzes your code</p>
              <p>• Generates comprehensive test cases</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// About component
const About: React.FC = () => {
  return (
    <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0">
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">About</h2>
          <p className="text-gray-600">
            This is an AI-powered test case generator that integrates with GitHub
            to automatically create comprehensive test cases for your codebase.
          </p>
        </div>
      </div>
    </div>
  )
}

export default App