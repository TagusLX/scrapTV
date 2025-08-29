// Test URL generation with corrected patterns
// Simulates the frontend generateIdealistaURL function

function generateIdealistaURL(region, location, operationType) {
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
}

function generatePropertyTypeURLs(region, location) {
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
}

// Test avec Conceicao e Cabanas de Tavira
const testRegion = "faro";
const testLocation = "tavira_conceicao-e-cabanas-de-tavira";

console.log("🧪 Testing URL Generation for 'Faro > Tavira > Conceicao e Cabanas de Tavira'");
console.log("=" * 80);

// Test URLs générales
const saleURL = generateIdealistaURL(testRegion, testLocation, 'sale');
const rentURL = generateIdealistaURL(testRegion, testLocation, 'rent');

console.log("📍 URLs Générales:");
console.log(`   Vente: ${saleURL}`);
console.log(`   Location: ${rentURL}`);

// Test URLs détaillées
const propertyURLs = generatePropertyTypeURLs(testRegion, testLocation);

console.log("\n📍 URLs Détaillées par Type:");
console.log("   VENTE:");
console.log(`     - Général: ${propertyURLs.sale.general}`);
console.log(`     - Appartements: ${propertyURLs.sale.apartments}`);
console.log(`     - Maisons: ${propertyURLs.sale.houses}`);
console.log(`     - Terrains urbains: ${propertyURLs.sale.urbanLand}`);
console.log(`     - Terrains agricoles: ${propertyURLs.sale.ruralLand}`);

console.log("   LOCATION:");
console.log(`     - Général: ${propertyURLs.rent.general}`);
console.log(`     - Appartements: ${propertyURLs.rent.apartments}`);
console.log(`     - Maisons: ${propertyURLs.rent.houses}`);

// Vérification avec les patterns attendus
console.log("\n✅ Vérification des Patterns:");
const expectedSale = "https://www.idealista.pt/comprar-casas/tavira/conceicao-e-cabanas-de-tavira/";
const expectedRent = "https://www.idealista.pt/arrendar-casas/tavira/conceicao-e-cabanas-de-tavira/com-arrendamento-longa-duracao/";

console.log(`   URL Vente correcte: ${saleURL === expectedSale ? '✅' : '❌'}`);
console.log(`   URL Location correcte: ${rentURL === expectedRent ? '✅' : '❌'}`);

if (saleURL === expectedSale && rentURL === expectedRent) {
    console.log("\n🎉 TOUS LES TESTS PASSÉS - URLs correctement générées !");
} else {
    console.log("\n❌ ÉCHEC DES TESTS - Vérifiez la logique de génération d'URL");
}