import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Database, FileText as FileTextIcon, BookOpen, Globe } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function DataCurationSection() {
  const { t } = useTranslation('home');

  return (
    <section className="mb-16">
      <h2 className="text-2xl font-semibold mb-4">{t('dataCurationSection.title')}</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card className="h-full">
          <CardHeader>
            <div className="flex items-center gap-3"><Database className="h-6 w-6 text-primary" /><CardTitle>{t('dataCurationSection.createDataProduct.title')}</CardTitle></div>
            <CardDescription>{t('dataCurationSection.createDataProduct.description')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild><Link to="/data-products">{t('dataCurationSection.createDataProduct.button')}</Link></Button>
          </CardContent>
        </Card>
        <Card className="h-full">
          <CardHeader>
            <div className="flex items-center gap-3"><FileTextIcon className="h-6 w-6 text-primary" /><CardTitle>{t('dataCurationSection.defineDataContract.title')}</CardTitle></div>
            <CardDescription>{t('dataCurationSection.defineDataContract.description')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild><Link to="/data-contracts">{t('dataCurationSection.defineDataContract.button')}</Link></Button>
          </CardContent>
        </Card>
        <Card className="h-full">
          <CardHeader>
            <div className="flex items-center gap-3"><BookOpen className="h-6 w-6 text-primary" /><CardTitle>{t('dataCurationSection.createDataset.title')}</CardTitle></div>
            <CardDescription>{t('dataCurationSection.createDataset.description')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline"><Link to="/master-data">{t('dataCurationSection.createDataset.button')}</Link></Button>
          </CardContent>
        </Card>
        <Card className="h-full">
          <CardHeader>
            <div className="flex items-center gap-3"><Globe className="h-6 w-6 text-primary" /><CardTitle>{t('dataCurationSection.createSchema.title')}</CardTitle></div>
            <CardDescription>{t('dataCurationSection.createSchema.description')}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Button asChild variant="outline"><Link to="/catalog-commander">{t('dataCurationSection.createSchema.openButton')}</Link></Button>
              <Button asChild><Link to="/create-uc">{t('dataCurationSection.createSchema.createButton')}</Link></Button>
            </div>
          </CardContent>
        </Card>
        <Card className="h-full">
          <CardHeader>
            <div className="flex items-center gap-3"><Globe className="h-6 w-6 text-primary" /><CardTitle>{t('dataCurationSection.createCatalog.title')}</CardTitle></div>
            <CardDescription>{t('dataCurationSection.createCatalog.description')}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Button asChild variant="outline"><Link to="/catalog-commander">{t('dataCurationSection.createCatalog.openButton')}</Link></Button>
              <Button asChild><Link to="/create-uc">{t('dataCurationSection.createCatalog.createButton')}</Link></Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}


