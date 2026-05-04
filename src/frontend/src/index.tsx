import React from "react";
import ReactDOM from "react-dom/client";
import { createHashRouter, RouterProvider } from "react-router-dom";
import { initializeIcons } from "@fluentui/react";
import { AppStateProvider } from './AppStateContext/AppStateContext';

import "./index.css";

import Layout from "./pages/layout/Layout";
import Chat from "./pages/chat/Chat";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import GraphExplorer from "./pages/GraphExplorer";
import DocumentBrowser from "./pages/DocumentBrowser";
import WorkflowDashboard from "./pages/WorkflowDashboard";

initializeIcons();

const router = createHashRouter([
    {
        path: "/",
        element: <LandingPage />
    },
    {
        path: "/login",
        element: <LoginPage />
    },
    {
        path: "/register",
        element: <RegisterPage />
    },
    {
        path: "/app",
        element: (
            <AppStateProvider>
                <Layout />
            </AppStateProvider>
        ),
        children: [
            {
                index: true,
                element: <Chat />
            },
            {
                path: "graph",
                element: <GraphExplorer />
            },
            {
                path: "documents",
                element: <DocumentBrowser />
            },
            {
                path: "workflows",
                element: <WorkflowDashboard />
            },
            {
                path: "*",
                lazy: () => import("./pages/NoPage")
            }
        ]
    },
    {
        path: "*",
        lazy: () => import("./pages/NoPage")
    }
]);

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
        <RouterProvider router={router} />
    </React.StrictMode>
);
