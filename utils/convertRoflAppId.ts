// Utility to convert ROFL Bech32 App ID from rofl.yaml to hex format

import * as fs from 'fs';
import * as yaml from 'js-yaml';
import * as path from 'path'; // Import path module
import { bech32 } from 'bech32'; // Use named import

interface RoflConfig {
  deployments?: {
    default?: {
      app_id?: string;
    };
  };
}

try {
  // 1. Read rofl.yaml
  // Construct path relative to the script's directory
  const roflConfigPath = path.join(__dirname, '../rofl.yaml');
  if (!fs.existsSync(roflConfigPath)) {
    console.error(`Error: ${roflConfigPath} not found.`);
    process.exit(1);
  }
  const fileContents = fs.readFileSync(roflConfigPath, 'utf8');
  const doc = yaml.load(fileContents) as RoflConfig; // Type assertion

  // 2. Extract the app_id
  const roflAppID = doc?.deployments?.default?.app_id;
  if (!roflAppID) {
    console.error('Error: Could not find deployments.default.app_id in rofl.yaml');
    process.exit(1);
  }

  // 3. Decode Bech32
  const decoded = bech32.decode(roflAppID); // Use the imported object directly
  if (decoded.prefix !== 'rofl') {
    console.error(`Error: Malformed ROFL app identifier prefix: ${decoded.prefix}. Expected 'rofl'.`);
    process.exit(1);
  }
  const rawAppIDBytes = Buffer.from(bech32.fromWords(decoded.words)); // Use Buffer directly

  // 4. Convert to hex and print
  const hexAppID = '0x' + rawAppIDBytes.toString('hex');
  console.log(hexAppID);

} catch (e: any) { // Catch with type 'any' or 'unknown'
  console.error('An error occurred:', e.message);
  process.exit(1);
}