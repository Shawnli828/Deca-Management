import { useMemo, useState } from 'react';
import { api } from '@/lib/api';
import type { Country, Product } from '@/lib/types';
import { codeFromName } from '@/lib/utils';

type ProductSettingsValue = {
  name: string;
  folder: string;
  reelFarmCode: string;
  logo?: string;
};

type UseProductCatalogOptions = {
  onStatus: (message: string, isError?: boolean) => void;
  onProductAdded?: (product: Product) => void;
  onCountrySettingsSaved?: () => void;
};

function readFileAsDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(reader.error || new Error('Logo 读取失败'));
    reader.readAsDataURL(file);
  });
}

export function useProductCatalog({ onStatus, onProductAdded, onCountrySettingsSaved }: UseProductCatalogOptions) {
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProductId, setSelectedProductId] = useState('');
  const [selectedCountryId, setSelectedCountryId] = useState('');
  const [editingProductId, setEditingProductId] = useState('');
  const [countrySettingsOpen, setCountrySettingsOpen] = useState(false);

  const selectedProduct = useMemo(() => products.find(product => product.id === selectedProductId) || products[0] || null, [products, selectedProductId]);
  const selectedCountry = useMemo(
    () => selectedProduct?.countries?.find(country => country.id === selectedCountryId) || selectedProduct?.countries?.[0] || null,
    [selectedProduct, selectedCountryId]
  );
  const editingProduct = useMemo(() => products.find(product => product.id === editingProductId) || null, [products, editingProductId]);

  function replaceProducts(nextProducts: Product[]) {
    setProducts(nextProducts);
    setSelectedProductId(nextProducts[0]?.id || '');
    setSelectedCountryId(nextProducts[0]?.countries?.[0]?.id || '');
  }

  async function saveProducts(nextProducts: Product[]) {
    setProducts(nextProducts);
    try {
      const payload = await api.saveData(nextProducts);
      setProducts(payload.data || nextProducts);
      onStatus('已保存到数据库');
      return true;
    } catch {
      onStatus('保存失败', true);
      return false;
    }
  }

  async function readProductLogo(file: File) {
    if (!file.type.startsWith('image/')) {
      onStatus('请选择图片文件', true);
      throw new Error('请选择图片文件');
    }
    return readFileAsDataUrl(file);
  }

  async function addProduct() {
    const name = window.prompt('输入产品名称');
    if (!name?.trim()) return;
    const newProduct: Product = {
      id: crypto.randomUUID(),
      name: name.trim(),
      folder: '甲方',
      owner_type: '甲方',
      logo: '',
      reelFarmCode: codeFromName(name),
      countries: [],
      creatorCount: 0,
      materialCount: 0,
      postCount: 0
    };
    const saved = await saveProducts([...products, newProduct]);
    if (saved) {
      setSelectedProductId(newProduct.id);
      setEditingProductId(newProduct.id);
      onProductAdded?.(newProduct);
      onStatus(`${newProduct.name} 已添加`);
    }
  }

  async function saveProductSettings(value: ProductSettingsValue) {
    const product = editingProduct;
    if (!product) return;
    const nextProducts = products.map(item => (
      item.id === product.id
        ? {
            ...item,
            name: value.name,
            folder: value.folder,
            owner_type: value.folder,
            reelFarmCode: value.reelFarmCode || item.reelFarmCode || codeFromName(value.name),
            logo: value.logo || ''
          }
        : item
    ));
    const saved = await saveProducts(nextProducts);
    if (saved) onStatus(`${value.name} 设置已保存`);
  }

  async function saveCountrySettings(countries: Country[]) {
    const product = selectedProduct;
    if (!product) return;
    const nextProducts = products.map(item => (
      item.id === product.id
        ? { ...item, countries }
        : item
    ));
    const saved = await saveProducts(nextProducts);
    if (saved) {
      const stillSelected = countries.some(country => country.id === selectedCountryId);
      setSelectedCountryId(stillSelected ? selectedCountryId : (countries[0]?.id || ''));
      onCountrySettingsSaved?.();
      onStatus(`${product.name} 国家/地区设置已保存`);
    }
  }

  return {
    products,
    setProducts,
    selectedProduct,
    selectedCountry,
    editingProduct,
    selectedProductId,
    selectedCountryId,
    editingProductId,
    countrySettingsOpen,
    setSelectedProductId,
    setSelectedCountryId,
    setEditingProductId,
    setCountrySettingsOpen,
    replaceProducts,
    addProduct,
    readProductLogo,
    saveProductSettings,
    saveCountrySettings
  };
}
