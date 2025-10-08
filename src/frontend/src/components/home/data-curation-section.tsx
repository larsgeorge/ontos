import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Globe, Sparkles, Database } from 'lucide-react';
import React from 'react';
import SelfServiceDialog from '@/components/data-contracts/self-service-dialog';

export default function DataCurationSection() {
  const { t } = useTranslation('home');
  const [isSelfServiceOpen, setIsSelfServiceOpen] = React.useState(false);
  const [initialType, setInitialType] = React.useState<'catalog' | 'schema' | 'table'>('table');

  return (
    <section className="mb-16">
      <h2 className="text-2xl font-semibold mb-4">{t('dataCurationSection.title')}</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card className="h-full">
          <CardHeader>
            <div className="flex items-center gap-3"><Database className="h-6 w-6 text-primary" /><CardTitle>{t('dataCurationSection.createDataset.title')}</CardTitle></div>
            <CardDescription>{t('dataCurationSection.createDataset.description')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="default" onClick={() => { setInitialType('table'); setIsSelfServiceOpen(true); }} className="flex items-center gap-2"><Sparkles className="h-4 w-4" /> Self-Service</Button>
          </CardContent>
        </Card>
        <Card className="h-full">
          <CardHeader>
            <div className="flex items-center gap-3"><Globe className="h-6 w-6 text-primary" /><CardTitle>{t('dataCurationSection.createSchema.title')}</CardTitle></div>
            <CardDescription>{t('dataCurationSection.createSchema.description')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="default" onClick={() => { setInitialType('schema'); setIsSelfServiceOpen(true); }} className="flex items-center gap-2"><Sparkles className="h-4 w-4" /> Self-Service</Button>
          </CardContent>
        </Card>
        <Card className="h-full">
          <CardHeader>
            <div className="flex items-center gap-3"><Globe className="h-6 w-6 text-primary" /><CardTitle>{t('dataCurationSection.createCatalog.title')}</CardTitle></div>
            <CardDescription>{t('dataCurationSection.createCatalog.description')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="default" onClick={() => { setInitialType('catalog'); setIsSelfServiceOpen(true); }} className="flex items-center gap-2"><Sparkles className="h-4 w-4" /> Self-Service</Button>
          </CardContent>
        </Card>
      </div>
      <SelfServiceDialog isOpen={isSelfServiceOpen} onOpenChange={setIsSelfServiceOpen} initialType={initialType} />
    </section>
  );
}


