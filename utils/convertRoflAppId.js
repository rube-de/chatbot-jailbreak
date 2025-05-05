"use strict";
// Utility to convert ROFL Bech32 App ID from rofl.yaml to hex format
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var _a, _b;
Object.defineProperty(exports, "__esModule", { value: true });
const fs = __importStar(require("fs"));
const yaml = __importStar(require("js-yaml"));
const path = __importStar(require("path")); // Import path module
const bech32_1 = require("bech32"); // Use named import
try {
    // 1. Read rofl.yaml
    // Construct path relative to the script's directory
    const roflConfigPath = path.join(__dirname, '../rofl.yaml');
    if (!fs.existsSync(roflConfigPath)) {
        console.error(`Error: ${roflConfigPath} not found.`);
        process.exit(1);
    }
    const fileContents = fs.readFileSync(roflConfigPath, 'utf8');
    const doc = yaml.load(fileContents); // Type assertion
    // 2. Extract the app_id
    const roflAppID = (_b = (_a = doc === null || doc === void 0 ? void 0 : doc.deployments) === null || _a === void 0 ? void 0 : _a.default) === null || _b === void 0 ? void 0 : _b.app_id;
    if (!roflAppID) {
        console.error('Error: Could not find deployments.default.app_id in rofl.yaml');
        process.exit(1);
    }
    // 3. Decode Bech32
    const decoded = bech32_1.bech32.decode(roflAppID); // Use the imported object directly
    if (decoded.prefix !== 'rofl') {
        console.error(`Error: Malformed ROFL app identifier prefix: ${decoded.prefix}. Expected 'rofl'.`);
        process.exit(1);
    }
    const rawAppIDBytes = Buffer.from(bech32_1.bech32.fromWords(decoded.words)); // Use Buffer directly
    // 4. Convert to hex and print
    const hexAppID = '0x' + rawAppIDBytes.toString('hex');
    console.log(hexAppID);
}
catch (e) { // Catch with type 'any' or 'unknown'
    console.error('An error occurred:', e.message);
    process.exit(1);
}
