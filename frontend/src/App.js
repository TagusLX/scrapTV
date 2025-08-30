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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./components/ui/select";
import { AlertCircle, Database, TrendingUp, MapPin, Play, Loader2, Download, Camera, Send, Eye, X, Filter, ExternalLink } from "lucide-react";
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
  const [coverageStats, setCoverageStats] = useState(null);
  const [districts, setDistricts] = useState([]);
  const [concelhos, setConcelhos] = useState([]);
  const [freguesias, setFreguesias] = useState([]);
  const [selectedDistrito, setSelectedDistrito] = useState("");
  const [selectedConcelho, setSelectedConcelho] = useState("");
  const [selectedFreguesia, setSelectedFreguesia] = useState("");
  const [selectedOperationType, setSelectedOperationType] = useState("");
  const [selectedPropertyType, setSelectedPropertyType] = useState("");
  const [detailedStats, setDetailedStats] = useState([]);

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
      // Build query parameters based on current filters
      const params = new URLSearchParams();
      params.append('limit', '50');
      
      if (selectedDistrito) {
        params.append('distrito', selectedDistrito);
      }
      if (selectedConcelho) {
        params.append('concelho', selectedConcelho);
      }
      if (selectedFreguesia) {
        params.append('freguesia', selectedFreguesia);
      }
      
      const response = await axios.get(`${API}/properties/filter?${params.toString()}`);
      setProperties(response.data);
    } catch (error) {
      console.error('Error fetching properties:', error);
    }
  };

  const fetchDetailedStats = async () => {
    try {
      // Build query parameters based on current filters
      const params = new URLSearchParams();
      
      if (selectedDistrito) {
        params.append('distrito', selectedDistrito);
      }
      if (selectedConcelho) {
        params.append('concelho', selectedConcelho);
      }
      if (selectedFreguesia) {
        params.append('freguesia', selectedFreguesia);
      }
      if (selectedOperationType) {
        params.append('operation_type', selectedOperationType);
      }
      if (selectedPropertyType) {
        params.append('property_type', selectedPropertyType);
      }
      
      const endpoint = `${API}/stats/detailed?${params.toString()}`;
      const response = await axios.get(endpoint);
      setDetailedStats(response.data);
    } catch (error) {
      console.error('Error fetching detailed stats:', error);
    }
  };

  const fetchRegionStats = async () => {
    try {
      // Build query parameters based on current filters
      const params = new URLSearchParams();
      
      if (selectedDistrito) {
        params.append('distrito', selectedDistrito);
      }
      if (selectedConcelho) {
        params.append('concelho', selectedConcelho);
      }
      if (selectedFreguesia) {
        params.append('freguesia', selectedFreguesia);
      }
      
      const endpoint = params.toString() ? `${API}/stats/filter?${params.toString()}` : `${API}/stats/regions`;
      const response = await axios.get(endpoint);
      setRegionStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const fetchCoverageStats = async () => {
    try {
      const response = await axios.get(`${API}/coverage/stats`);
      setCoverageStats(response.data);
    } catch (error) {
      console.error('Error fetching coverage stats:', error);
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

  const fetchDistricts = async () => {
    try {
      const response = await axios.get(`${API}/administrative/districts`);
      setDistricts(response.data.districts || []);
    } catch (error) {
      console.error('Error fetching districts:', error);
    }
  };

  const fetchConcelhos = async (distrito) => {
    try {
      if (!distrito) {
        setConcelhos([]);
        return;
      }
      const response = await axios.get(`${API}/administrative/districts/${distrito}/concelhos`);
      setConcelhos(response.data.concelhos || []);
    } catch (error) {
      console.error('Error fetching concelhos:', error);
      setConcelhos([]);
    }
  };

  const fetchFreguesias = async (distrito, concelho) => {
    try {
      if (!distrito || !concelho) {
        setFreguesias([]);
        return;
      }
      const response = await axios.get(`${API}/administrative/districts/${distrito}/concelhos/${concelho}/freguesias`);
      setFreguesias(response.data.freguesias || []);
    } catch (error) {
      console.error('Error fetching freguesias:', error);
      setFreguesias([]);
    }
  };

  const handleDistritoChange = (distrito) => {
    const selectedValue = distrito === "all" ? "" : distrito;
    setSelectedDistrito(selectedValue);
    setSelectedConcelho("");
    setSelectedFreguesia("");
    setConcelhos([]);
    setFreguesias([]);
    
    if (selectedValue) {
      fetchConcelhos(selectedValue);
    }
  };

  const handleConcelhoChange = (concelho) => {
    const selectedValue = concelho === "all" ? "" : concelho;
    setSelectedConcelho(selectedValue);
    setSelectedFreguesia("");
    setFreguesias([]);
    
    if (selectedValue && selectedDistrito) {
      fetchFreguesias(selectedDistrito, selectedValue);
    }
  };

  const handleFrequesiaChange = (freguesia) => {
    const selectedValue = freguesia === "all" ? "" : freguesia;
    setSelectedFreguesia(selectedValue);
  };

  const applyFilters = () => {
    fetchProperties();
    fetchRegionStats();
    fetchDetailedStats();
  };

  const clearFilters = () => {
    setSelectedDistrito("");
    setSelectedConcelho("");
    setSelectedFreguesia("");
    setSelectedOperationType("");
    setSelectedPropertyType("");
    setConcelhos([]);
    setFreguesias([]);
    // Fetch unfiltered data
    fetchProperties();
    fetchRegionStats();
    fetchDetailedStats();
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

  const generateIdealistaURL = (region, location, operationType) => {
    if (!region || !location) return null;
    
    // Parse location (formato: concelho_freguesia)
    if (!location.includes('_')) return null;
    
    const [concelho, freguesia] = location.split('_', 2);
    const cleanConcelho = concelho.toLowerCase().replace(/\s+/g, '-');
    const cleanFreguesia = freguesia.toLowerCase().replace(/\s+/g, '-');
    
    if (operationType === 'sale') {
      // URL pour la vente générale (casas + appartements + maisons)
      return `https://www.idealista.pt/comprar-casas/${cleanConcelho}/${cleanFreguesia}/`;
    } else {
      // URL pour la location générale (arrendamento longa duracao)
      return `https://www.idealista.pt/arrendar-casas/${cleanConcelho}/${cleanFreguesia}/com-arrendamento-longa-duracao/`;
    }
  };

  const generatePropertyTypeURLs = (region, location) => {
    if (!region || !location || !location.includes('_')) return {};
    
    const [concelho, freguesia] = location.split('_', 2);
    const cleanConcelho = concelho.toLowerCase().replace(/\s+/g, '-');
    const cleanFreguesia = freguesia.toLowerCase().replace(/\s+/g, '-');
    
    return {
      sale: {
        general: `https://www.idealista.pt/comprar-casas/${cleanConcelho}/${cleanFreguesia}/`,
        apartments: `https://www.idealista.pt/comprar-casas/${cleanConcelho}/${cleanFreguesia}/com-apartamentos/`,
        houses: `https://www.idealista.pt/comprar-casas/${cleanConcelho}/${cleanFreguesia}/com-moradias/`,
        urbanLand: `https://www.idealista.pt/comprar-terrenos/${cleanConcelho}/${cleanFreguesia}/com-terreno-urbano/`,
        ruralLand: `https://www.idealista.pt/comprar-terrenos/${cleanConcelho}/${cleanFreguesia}/com-terreno-nao-urbanizavel/`
      },
      rent: {
        general: `https://www.idealista.pt/arrendar-casas/${cleanConcelho}/${cleanFreguesia}/com-arrendamento-longa-duracao/`,
        apartments: `https://www.idealista.pt/arrendar-casas/${cleanConcelho}/${cleanFreguesia}/com-apartamentos,arrendamento-longa-duracao/`,
        houses: `https://www.idealista.pt/arrendar-casas/${cleanConcelho}/${cleanFreguesia}/com-moradias,arrendamento-longa-duracao/`
      }
    };
  };

  // Effect to fetch data when filters change
  useEffect(() => {
    applyFilters();
  }, [selectedDistrito, selectedConcelho, selectedFreguesia, selectedOperationType, selectedPropertyType]);

  useEffect(() => {
    fetchScrapingSessions();
    fetchProperties();
    fetchRegionStats();
    fetchCoverageStats();
    fetchDistricts();
    fetchDetailedStats();
    
    // Poll for sessions every 5 seconds to check for CAPTCHAs
    const pollInterval = setInterval(() => {
      fetchScrapingSessions();
      fetchCoverageStats(); // Also update coverage
    }, 5000);
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

            {/* Coverage Stats */}
            {coverageStats && (
              <div className="mt-6 p-4 bg-gradient-to-r from-indigo-50 to-blue-50 rounded-lg">
                <h3 className="font-semibold mb-2">Couverture Administrative</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="font-medium">Distritos:</span> {coverageStats.covered_districts}/{coverageStats.total_districts}
                  </div>
                  <div>
                    <span className="font-medium">Concelhos:</span> {coverageStats.covered_municipalities}/{coverageStats.total_municipalities}
                  </div>
                  <div>
                    <span className="font-medium">Freguesias:</span> {coverageStats.covered_parishes}/{coverageStats.total_parishes}
                  </div>
                  <div>
                    <span className="font-medium">Couverture:</span> <strong>{coverageStats.overall_coverage_percentage}%</strong>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Filtering Panel */}
        <Card className="border-0 shadow-lg bg-white/70 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="h-5 w-5 text-green-600" />
              Filtrer par Région Administrative
            </CardTitle>
            <CardDescription>
              Filtrer les données par Distrito, Concelho et Freguesia
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* First Row - Administrative Filters */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* Distrito Filter */}
              <div className="space-y-2">
                <Label>Distrito</Label>
                <Select value={selectedDistrito || "all"} onValueChange={handleDistritoChange}>
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner un distrito" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tous les distritos</SelectItem>
                    {districts.map((distrito) => (
                      <SelectItem key={distrito.id} value={distrito.id}>
                        {distrito.name_display}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Concelho Filter */}
              <div className="space-y-2">
                <Label>Concelho</Label>
                <Select 
                  value={selectedConcelho || "all"}
                  onValueChange={handleConcelhoChange}
                  disabled={!selectedDistrito}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner un concelho" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tous les concelhos</SelectItem>
                    {concelhos.map((concelho) => (
                      <SelectItem key={concelho.id} value={concelho.id}>
                        {concelho.name_display}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Freguesia Filter */}
              <div className="space-y-2">
                <Label>Freguesia</Label>
                <Select 
                  value={selectedFreguesia || "all"}
                  onValueChange={handleFrequesiaChange}
                  disabled={!selectedConcelho}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner une freguesia" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Toutes les freguesias</SelectItem>
                    {freguesias.map((freguesia) => (
                      <SelectItem key={freguesia.id} value={freguesia.id}>
                        {freguesia.name_display}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Clear Filters Button */}
              <div className="space-y-2">
                <Label>&nbsp;</Label>
                <Button 
                  onClick={clearFilters} 
                  variant="outline" 
                  className="w-full"
                  disabled={!selectedDistrito && !selectedConcelho && !selectedFreguesia && !selectedOperationType && !selectedPropertyType}
                >
                  Effacer Filtres
                </Button>
              </div>
            </div>

            {/* Second Row - Property Type and Operation Filters */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Operation Type Filter */}
              <div className="space-y-2">
                <Label>Type d'Opération</Label>
                <Select 
                  value={selectedOperationType || "all"} 
                  onValueChange={(value) => setSelectedOperationType(value === "all" ? "" : value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Vente ou Location" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Vente et Location</SelectItem>
                    <SelectItem value="sale">Vente uniquement</SelectItem>
                    <SelectItem value="rent">Location uniquement</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Property Type Filter */}
              <div className="space-y-2">
                <Label>Type de Bien</Label>
                <Select 
                  value={selectedPropertyType || "all"} 
                  onValueChange={(value) => setSelectedPropertyType(value === "all" ? "" : value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Tous types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tous les types</SelectItem>
                    <SelectItem value="apartment">Appartements</SelectItem>
                    <SelectItem value="house">Maisons</SelectItem>
                    <SelectItem value="plot">Terrains (tous)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Spacer */}
              <div></div>
            </div>

            {/* Filter Summary */}
            {(selectedDistrito || selectedConcelho || selectedFreguesia || selectedOperationType || selectedPropertyType) && (
              <div className="p-3 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-800">
                  <strong>Filtres actifs:</strong> 
                  {[
                    selectedDistrito && districts.find(d => d.id === selectedDistrito)?.name_display,
                    selectedConcelho && concelhos.find(c => c.id === selectedConcelho)?.name_display,
                    selectedFreguesia && freguesias.find(f => f.id === selectedFreguesia)?.name_display,
                    selectedOperationType && (selectedOperationType === 'sale' ? 'Vente' : 'Location'),
                    selectedPropertyType && {
                      'apartment': 'Appartements',
                      'house': 'Maisons', 
                      'plot': 'Terrains'
                    }[selectedPropertyType]
                  ].filter(Boolean).join(' • ')}
                </p>
              </div>
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
                      <p className="text-sm font-medium text-gray-600">Zones de Prix</p>
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

            {/* Detailed Regional Overview */}
            {detailedStats.length > 0 && (
              <Card className="border-0 shadow-lg bg-white/70 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle>Aperçu Détaillé par Type de Bien</CardTitle>
                  <CardDescription>Prix détaillés par type de propriété et opération</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {detailedStats.slice(0, 6).map((stat, index) => {
                      const saleURL = generateIdealistaURL(stat.region, stat.location, 'sale');
                      const rentURL = generateIdealistaURL(stat.region, stat.location, 'rent');
                      const propertyURLs = generatePropertyTypeURLs(stat.region, stat.location);
                      
                      // Group detailed stats by property type and operation
                      const groupedStats = {};
                      stat.detailed_stats.forEach(detail => {
                        const key = detail.property_type;
                        if (!groupedStats[key]) {
                          groupedStats[key] = { sale: null, rent: null };
                        }
                        groupedStats[key][detail.operation_type] = detail;
                      });
                      
                      return (
                        <div key={index} className="p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg">
                          <h4 className="font-semibold text-gray-900 mb-4">
                            {stat.display_info ? stat.display_info.full_display : `${stat.region} - ${stat.location}`}
                          </h4>
                          
                          <div className="space-y-4 text-sm">
                            {/* Property Type Breakdown */}
                            {Object.entries(groupedStats).map(([propType, operations]) => {
                              const typeNames = {
                                'apartment': '🏢 Appartements',
                                'house': '🏠 Maisons',
                                'plot': '📐 Terrains'
                              };
                              const typeName = typeNames[propType] || propType;
                              
                              return (
                                <div key={propType} className="border-l-4 border-blue-300 pl-3">
                                  <h5 className="font-medium text-gray-800 mb-2">{typeName}</h5>
                                  <div className="grid grid-cols-2 gap-3 text-xs">
                                    {/* Sale */}
                                    <div className="space-y-1">
                                      <div className="flex items-center justify-between">
                                        <span className="text-blue-700 font-medium">
                                          Vente: {operations.sale?.avg_price_per_sqm ? `${operations.sale.avg_price_per_sqm.toFixed(0)} €/m²` : 'N/A'}
                                        </span>
                                        {propertyURLs.sale?.[propType === 'plot' ? 'urbanLand' : propType + 's'] && (
                                          <a 
                                            href={propertyURLs.sale[propType === 'plot' ? 'urbanLand' : propType + 's']} 
                                            target="_blank" 
                                            rel="noopener noreferrer"
                                            className="text-blue-600 hover:text-blue-800"
                                            title={`Voir ${typeName} vente`}
                                          >
                                            <ExternalLink className="h-3 w-3" />
                                          </a>
                                        )}
                                      </div>
                                      {operations.sale && (
                                        <span className="text-gray-600">{operations.sale.count} biens</span>
                                      )}
                                    </div>
                                    
                                    {/* Rent */}
                                    <div className="space-y-1">
                                      <div className="flex items-center justify-between">
                                        <span className="text-green-700 font-medium">
                                          Location: {operations.rent?.avg_price_per_sqm ? `${operations.rent.avg_price_per_sqm.toFixed(0)} €/m²` : 'N/A'}
                                        </span>
                                        {propertyURLs.rent?.[propType + 's'] && propType !== 'plot' && (
                                          <a 
                                            href={propertyURLs.rent[propType + 's']} 
                                            target="_blank" 
                                            rel="noopener noreferrer"
                                            className="text-green-600 hover:text-green-800"
                                            title={`Voir ${typeName} location`}
                                          >
                                            <ExternalLink className="h-3 w-3" />
                                          </a>
                                        )}
                                      </div>
                                      {operations.rent && (
                                        <span className="text-gray-600">{operations.rent.count} biens</span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                          
                          <div className="mt-4 pt-3 border-t border-blue-200 text-xs text-gray-600">
                            Total zones: {stat.total_properties}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Fallback: General Regional Overview */}
            {detailedStats.length === 0 && regionStats.length > 0 && (
              <Card className="border-0 shadow-lg bg-white/70 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle>Aperçu Régional Rapide</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {regionStats.slice(0, 6).map((stat, index) => {
                      const saleURL = generateIdealistaURL(stat.region, stat.location, 'sale');
                      const rentURL = generateIdealistaURL(stat.region, stat.location, 'rent');
                      const propertyURLs = generatePropertyTypeURLs(stat.region, stat.location);
                      
                      return (
                        <div key={index} className="p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg">
                          <h4 className="font-semibold text-gray-900 mb-3">
                            {stat.display_info ? stat.display_info.full_display : `${stat.region} - ${stat.location}`}
                          </h4>
                          <div className="space-y-3 text-sm">
                            {/* Vente */}
                            <div className="space-y-1">
                              <div className="flex items-center justify-between">
                                <span className="font-medium text-blue-800">Vente: {stat.avg_sale_price_per_sqm ? `${stat.avg_sale_price_per_sqm.toFixed(0)} €/m²` : 'N/A'}</span>
                                {saleURL && (
                                  <a 
                                    href={saleURL} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    className="ml-2 text-blue-600 hover:text-blue-800 transition-colors"
                                    title="Voir les ventes sur Idealista.pt"
                                  >
                                    <ExternalLink className="h-3 w-3" />
                                  </a>
                                )}
                              </div>
                              {propertyURLs.sale && (
                                <div className="flex gap-1 text-xs">
                                  <a href={propertyURLs.sale.apartments} target="_blank" rel="noopener noreferrer" 
                                     className="text-blue-500 hover:underline" title="Appartements">App</a>
                                  <span>•</span>
                                  <a href={propertyURLs.sale.houses} target="_blank" rel="noopener noreferrer"
                                     className="text-blue-500 hover:underline" title="Maisons">Maisons</a>
                                  <span>•</span>
                                  <a href={propertyURLs.sale.urbanLand} target="_blank" rel="noopener noreferrer"
                                     className="text-blue-500 hover:underline" title="Terrains urbains">T.Urb</a>
                                  <span>•</span>
                                  <a href={propertyURLs.sale.ruralLand} target="_blank" rel="noopener noreferrer"
                                     className="text-blue-500 hover:underline" title="Terrains agricoles">T.Agr</a>
                                </div>
                              )}
                            </div>

                            {/* Location */}
                            <div className="space-y-1">
                              <div className="flex items-center justify-between">
                                <span className="font-medium text-green-800">Location: {stat.avg_rent_price_per_sqm ? `${stat.avg_rent_price_per_sqm.toFixed(0)} €/m²` : 'N/A'}</span>
                                {rentURL && (
                                  <a 
                                    href={rentURL} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    className="ml-2 text-green-600 hover:text-green-800 transition-colors"
                                    title="Voir les locations sur Idealista.pt"
                                  >
                                    <ExternalLink className="h-3 w-3" />
                                  </a>
                                )}
                              </div>
                              {propertyURLs.rent && (
                                <div className="flex gap-1 text-xs">
                                  <a href={propertyURLs.rent.apartments} target="_blank" rel="noopener noreferrer"
                                     className="text-green-500 hover:underline" title="Appartements location">App</a>
                                  <span>•</span>
                                  <a href={propertyURLs.rent.houses} target="_blank" rel="noopener noreferrer"
                                     className="text-green-500 hover:underline" title="Maisons location">Maisons</a>
                                </div>
                              )}
                            </div>

                            <p className="pt-2 border-t border-blue-200 text-gray-600">Zones Prix: {stat.total_properties}</p>
                          </div>
                        </div>
                      );
                    })}
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
                        <h4 className="font-medium">
                          {property.display_info ? property.display_info.full_display : `${property.region} - ${property.location}`}
                        </h4>
                        <div className="space-y-1 text-sm text-gray-600">
                          {property.price && (
                            <p>Prix: {formatCurrency(property.price)}</p>
                          )}
                          {property.area && (
                            <p>Surface: {property.area} m²</p>
                          )}
                          {property.price_per_sqm && (
                            <p>€/m²: {property.price_per_sqm.toFixed(0)} €/m²</p>
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
                      <h4 className="font-bold text-lg mb-4">
                        {stat.display_info ? stat.display_info.full_display : `${stat.region} - ${stat.location}`}
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
                          Zones Prix Totales: <span className="font-medium">{stat.total_properties}</span>
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