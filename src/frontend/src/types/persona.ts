export interface Persona {
  id: string;
  name: string;
  description: string;
  privileges: Privilege[];
  groups: string[];  // Add groups array
  created: string;
  updated: string;
}

export interface Privilege {
  securableId: string;
  securableType: 'CATALOG' | 'SCHEMA' | 'TABLE' | 'VIEW' | 'FUNCTION';
  securableName: string;
  permission: 'READ' | 'WRITE' | 'MANAGE';
}

export interface NewPersona {
  name: string;
  description: string;
  groups?: string[];  // Optional for creation
} 