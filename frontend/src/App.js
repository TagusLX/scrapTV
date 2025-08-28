import React, { useState, useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import { AlertCircle, Database, TrendingUp, MapPin, Play, Loader2, Download, Camera, Send, Eye, X } from "lucide-react";
import { Alert, AlertDescription } from "./components/ui/alert";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "./components/ui/dialog";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = () => {
  const [scrapingSessions, setScrapingSessions] = useState([]);
  const [properties, setProperties] = useState([]);
  const [regionStats, setRegionStats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentSession, setCurrentSession] = useState(null);
  const [captchaSession, setCaptchaSession] = useState(null);
  const [captchaImage, setCaptchaImage] = useState(null);
  const [captchaSolution, setCaptchaSolution] = useState("");
  const [showCaptchaDialog, setShowCaptchaDialog] = useState(false);
  const [solvingCaptcha, setSolvingCaptcha] = useState(false);

  const fetchScrapingSessions = async () => {
    try {
      const response = await axios.get(`${API}/scraping-sessions`);
      setScrapingSessions(response.data);
      
      // Check if any session is waiting for CAPTCHA
      const waitingSession = response.data.find(session => session.status === 'waiting_captcha');
      if (waitingSession && waitingSession.id !== captchaSession?.id) {
        setCaptchaSession(waitingSession);
        await fetchCaptchaImage(waitingSession.id);
        setShowCaptchaDialog(true);
      }
    } catch (error) {
      console.error('Error fetching sessions:', error);
    }
  };

  const fetchCaptchaImage = async (sessionId) => {
    try {
      const imageUrl = `${BACKEND_URL}/captcha/${sessionId}`;
      setCaptchaImage(imageUrl);
    } catch (error) {
      console.error('Error fetching CAPTCHA image:', error);
    }
  };

  const solveCaptcha = async () => {
    if (!captchaSession || !captchaSolution.trim()) return;
    
    try {
      setSolvingCaptcha(true);
      const response = await axios.post(`${API}/captcha/${captchaSession.id}/solve`, {
        solution: captchaSolution
      });
      
      if (response.data.message === "CAPTCHA solved successfully") {
        setShowCaptchaDialog(false);
        setCaptchaSession(null);
        setCaptchaImage(null);
        setCaptchaSolution("");
        // Continue monitoring the session
        await fetchScrapingSessions();
      } else {
        alert("CAPTCHA incorret. Veuillez réessayer.");
      }
    } catch (error) {
      console.error('Error solving CAPTCHA:', error);
      alert("Erreur lors de la résolution du CAPTCHA");
    } finally {
      setSolvingCaptcha(false);
    }
  };

  const fetchProperties = async () => {
    try {
      const response = await axios.get(`${API}/properties?limit=50`);
      setProperties(response.data);
    } catch (error) {
      console.error('Error fetching properties:', error);
    }
  };

  const fetchRegionStats = async () => {
    try {
      const response = await axios.get(`${API}/stats/regions`);
      setRegionStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const startScraping = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`${API}/scrape/start`);
      setCurrentSession(response.data.session_id);
      
      // Poll for session updates
      const pollInterval = setInterval(async () => {
        try {
          const sessionResponse = await axios.get(`${API}/scraping-sessions/${response.data.session_id}`);
          const session = sessionResponse.data;
          
          if (session.status === 'completed' || session.status === 'failed') {
            clearInterval(pollInterval);
            setLoading(false);
            setCurrentSession(null);
            fetchScrapingSessions();
            fetchProperties();
            fetchRegionStats();
          } else if (session.status === 'waiting_captcha') {
            // CAPTCHA will be handled by fetchScrapingSessions polling
          }
        } catch (error) {
          console.error('Error polling session:', error);
          clearInterval(pollInterval);
          setLoading(false);
        }
      }, 3000);
      
    } catch (error) {
      console.error('Error starting scraping:', error);
      setLoading(false);
    }
  };

  const exportPhpData = async () => {
    try {
      const response = await axios.get(`${API}/export/php`);
      const phpCode = generatePhpCode(response.data.php_array);
      
      // Create downloadable file
      const blob = new Blob([phpCode], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'market_data.php';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error exporting PHP data:', error);
    }
  };

  const generatePhpCode = (data) => {
    const timestamp = new Date().toLocaleString('pt-PT');
    
    let phpCode = `<?php
/**
 * Market prices data for Portugal
 * Last update ${timestamp}
 * Generated by Idealista Scraper with CAPTCHA handling
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

/**
 * Get market data for Portuguese real estate
 *
 * @return array Market data by region
 */
function tagus_value_get_market_data() {
    return ${phpArrayToString(data, 1)};
}
`;
    return phpCode;
  };

  const phpArrayToString = (obj, indent = 0) => {
    const spaces = '    '.repeat(indent);
    if (Array.isArray(obj)) {
      return 'array()';
    }
    
    let result = 'array(\n';
    for (const [key, value] of Object.entries(obj)) {
      result += `${spaces}    '${key}' => `;
      if (typeof value === 'object' && value !== null) {
        result += phpArrayToString(value, indent + 1);
      } else if (typeof value === 'string') {
        result += `'${value}'`;
      } else {
        result += value;
      }
      result += ',\n';
    }
    result += `${spaces})`;
    return result;
  };

  const clearAllData = async () => {
    try {
      await axios.delete(`${API}/properties`);
      setProperties([]);
      setRegionStats([]);
    } catch (error) {
      console.error('Error clearing data:', error);
    }
  };

  useEffect(() => {
    fetchScrapingSessions();
    fetchProperties();
    fetchRegionStats();
    
    // Poll for sessions every 5 seconds to check for CAPTCHAs
    const pollInterval = setInterval(fetchScrapingSessions, 5000);
    return () => clearInterval(pollInterval);
  }, []);

  const formatCurrency = (value) => {
    if (!value) return '€0';
    return new Intl.NumberFormat('pt-PT', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const getStatusBadgeColor = (status) => {
    switch (status) {
      case 'completed':
        return 'default';
      case 'running':
        return 'secondary';
      case 'waiting_captcha':
        return 'destructive';
      case 'failed':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'waiting_captcha':
        return 'En attente CAPTCHA';
      case 'running':
        return 'En cours';
      case 'completed':
        return 'Terminé';
      case 'failed':
        return 'Échoué';
      default:
        return status;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Idealista Portugal Scraper
          </h1>
          <p className="text-xl text-gray-600">
            Monitor Portuguese real estate market prices with CAPTCHA handling
          </p>
        </div>

        {/* CAPTCHA Dialog */}
        <Dialog open={showCaptchaDialog} onOpenChange={setShowCaptchaDialog}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Camera className="h-5 w-5 text-orange-600" />
                Résoudre le CAPTCHA
              </DialogTitle>
              <DialogDescription>
                Un CAPTCHA a été détecté. Veuillez saisir le code pour continuer le scraping.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4">
              {captchaImage && (
                <div className="border rounded-lg overflow-hidden bg-gray-100 flex justify-center">
                  <img 
                    src={captchaImage} 
                    alt="CAPTCHA" 
                    className="max-w-full h-auto"
                    style={{ maxHeight: '200px' }}
                  />
                </div>
              )}
              
              <div className="space-y-2">
                <Label htmlFor="captcha-solution">Code CAPTCHA</Label>
                <Input
                  id="captcha-solution"
                  type="text"
                  placeholder="Entrez le code CAPTCHA"
                  value={captchaSolution}
                  onChange={(e) => setCaptchaSolution(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && solveCaptcha()}
                />
              </div>
              
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowCaptchaDialog(false);
                    setCaptchaSolution("");
                  }}
                >
                  <X className="h-4 w-4 mr-2" />
                  Annuler
                </Button>
                <Button
                  onClick={solveCaptcha}
                  disabled={!captchaSolution.trim() || solvingCaptcha}
                  className="bg-gradient-to-r from-green-600 to-green-700"
                >
                  {solvingCaptcha ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Résolution...
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4 mr-2" />
                      Soumettre
                    </>
                  )}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* Control Panel */}
        <Card className="border-0 shadow-lg bg-white/70 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5 text-blue-600" />
              Panneau de Contrôle du Scraping
            </CardTitle>
            <CardDescription>
              Démarrer le scraping des prix immobiliers de toutes les régions portugaises avec gestion CAPTCHA
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-4 flex-wrap">
              <Button
                onClick={startScraping}
                disabled={loading}
                className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Scraping en cours...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Démarrer le Scraping
                  </>
                )}
              </Button>
              
              <Button onClick={exportPhpData} variant="outline">
                <Download className="h-4 w-4 mr-2" />
                Exporter PHP
              </Button>
              
              <Button onClick={clearAllData} variant="outline" className="text-red-600 hover:text-red-700">
                Effacer les Données
              </Button>
            </div>
            
            {loading && (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Scraping en cours... Cela peut prendre plusieurs minutes. Si un CAPTCHA apparaît, vous serez invité à le résoudre.
                </AlertDescription>
              </Alert>
            )}

            {captchaSession && (
              <Alert className="border-orange-200 bg-orange-50">
                <Camera className="h-4 w-4 text-orange-600" />
                <AlertDescription className="text-orange-800">
                  <strong>CAPTCHA détecté!</strong> Session {captchaSession.id.slice(0, 8)} en attente de résolution CAPTCHA.
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Main Content */}
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 bg-white/50 backdrop-blur-sm">
            <TabsTrigger value="overview">Aperçu</TabsTrigger>
            <TabsTrigger value="sessions">Sessions</TabsTrigger>
            <TabsTrigger value="properties">Propriétés</TabsTrigger>
            <TabsTrigger value="stats">Statistiques</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card className="border-0 shadow-lg bg-white/70 backdrop-blur-sm">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">Propriétés Totales</p>
                      <p className="text-2xl font-bold text-gray-900">{properties.length}</p>
                    </div>
                    <Database className="h-8 w-8 text-blue-600" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-lg bg-white/70 backdrop-blur-sm">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">Régions Couvertes</p>
                      <p className="text-2xl font-bold text-gray-900">{regionStats.length}</p>
                    </div>
                    <MapPin className="h-8 w-8 text-green-600" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-lg bg-white/70 backdrop-blur-sm">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">Sessions de Scraping</p>
                      <p className="text-2xl font-bold text-gray-900">{scrapingSessions.length}</p>
                    </div>
                    <TrendingUp className="h-8 w-8 text-purple-600" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {regionStats.length > 0 && (
              <Card className="border-0 shadow-lg bg-white/70 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle>Aperçu Régional Rapide</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {regionStats.slice(0, 6).map((stat, index) => (
                      <div key={index} className="p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg">
                        <h4 className="font-semibold capitalize text-gray-900">{stat.region} - {stat.location}</h4>
                        <div className="space-y-1 text-sm">
                          <p>Vente Moy: {formatCurrency(stat.avg_sale_price)}</p>
                          <p>Location Moy: {formatCurrency(stat.avg_rent_price)}</p>
                          <p>Propriétés: {stat.total_properties}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="sessions">
            <Card className="border-0 shadow-lg bg-white/70 backdrop-blur-sm">
              <CardHeader>
                <CardTitle>Historique des Sessions de Scraping</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {scrapingSessions.map((session) => (
                    <div key={session.id} className="p-4 border rounded-lg bg-white/50">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">Session {session.id.slice(0, 8)}</p>
                          <p className="text-sm text-gray-600">
                            Démarrée: {new Date(session.started_at).toLocaleString('fr-FR')}
                          </p>
                          {session.completed_at && (
                            <p className="text-sm text-gray-600">
                              Terminée: {new Date(session.completed_at).toLocaleString('fr-FR')}
                            </p>
                          )}
                        </div>
                        <div className="text-right">
                          <Badge variant={getStatusBadgeColor(session.status)}>
                            {getStatusText(session.status)}
                          </Badge>
                          <p className="text-sm text-gray-600 mt-1">
                            {session.total_properties} propriétés
                          </p>
                        </div>
                      </div>
                      {session.error_message && (
                        <Alert className="mt-3">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription>{session.error_message}</AlertDescription>
                        </Alert>
                      )}
                      {session.status === 'waiting_captcha' && (
                        <div className="mt-3 flex items-center gap-2">
                          <Camera className="h-4 w-4 text-orange-600" />
                          <span className="text-sm text-orange-600 font-medium">
                            En attente de résolution CAPTCHA
                          </span>
                          {session.id === captchaSession?.id && (
                            <Button
                              size="sm"
                              onClick={() => setShowCaptchaDialog(true)}
                              className="ml-2"
                            >
                              <Eye className="h-3 w-3 mr-1" />
                              Voir CAPTCHA
                            </Button>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="properties">
            <Card className="border-0 shadow-lg bg-white/70 backdrop-blur-sm">
              <CardHeader>
                <CardTitle>Propriétés Récentes</CardTitle>
                <CardDescription>Dernières propriétés scrapées depuis idealista.pt</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {properties.slice(0, 12).map((property) => (
                    <div key={property.id} className="p-4 border rounded-lg bg-white/50 hover:bg-white/70 transition-colors">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <Badge variant="outline" className="capitalize">
                            {property.property_type}
                          </Badge>
                          <Badge variant={property.operation_type === 'sale' ? 'default' : 'secondary'}>
                            {property.operation_type === 'sale' ? 'Vente' : 'Location'}
                          </Badge>
                        </div>
                        <h4 className="font-medium capitalize">
                          {property.region} - {property.location}
                        </h4>
                        <div className="space-y-1 text-sm text-gray-600">
                          {property.price && (
                            <p>Prix: {formatCurrency(property.price)}</p>
                          )}
                          {property.area && (
                            <p>Surface: {property.area} m²</p>
                          )}
                          {property.price_per_sqm && (
                            <p>€/m²: {formatCurrency(property.price_per_sqm)}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="stats">
            <Card className="border-0 shadow-lg bg-white/70 backdrop-blur-sm">
              <CardHeader>
                <CardTitle>Statistiques Régionales</CardTitle>
                <CardDescription>Données de marché agrégées par région et localisation</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {regionStats.map((stat, index) => (
                    <div key={index} className="p-6 border rounded-lg bg-gradient-to-r from-blue-50 to-purple-50">
                      <h4 className="font-bold text-lg capitalize mb-4">
                        {stat.region} - {stat.location}
                      </h4>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-sm font-medium text-gray-600">Prix de Vente (€/m²)</p>
                          <p className="text-xl font-bold text-blue-700">
                            {stat.avg_sale_price_per_sqm ? `${stat.avg_sale_price_per_sqm.toFixed(0)} €/m²` : 'N/A'}
                          </p>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-600">Prix de Location (€/m²)</p>
                          <p className="text-xl font-bold text-green-700">
                            {stat.avg_rent_price_per_sqm ? `${stat.avg_rent_price_per_sqm.toFixed(0)} €/m²` : 'N/A'}
                          </p>
                        </div>
                      </div>
                      <div className="mt-4 pt-4 border-t">
                        <p className="text-sm text-gray-600">
                          Propriétés Totales: <span className="font-medium">{stat.total_properties}</span>
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;