import React, { useState } from 'react';
import {
  Modal,
  Space,
  Button,
  Upload,
  Select,
  Alert,
  Progress,
  Typography,
  Divider,
  message,
  Radio,
  Checkbox,
} from 'antd';
import {
  DownloadOutlined,
  UploadOutlined,
  FileExcelOutlined,
  FilePdfOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import api from '../services/api';

const { Text } = Typography;
const { Option } = Select;

interface ExportImportProps {
  visible: boolean;
  onClose: () => void;
  mode: 'export' | 'import';
  selectedProductIds?: number[];
}

const ExportImport: React.FC<ExportImportProps> = ({
  visible,
  onClose,
  mode,
  selectedProductIds = [],
}) => {
  const [exportFormat, setExportFormat] = useState<'csv' | 'excel' | 'pdf'>('excel');
  const [exportFields, setExportFields] = useState<string[]>([
    'id',
    'name',
    'brand',
    'part_number',
    'price',
    'stock',
  ]);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [importResult, setImportResult] = useState<any>(null);

  const allFields = [
    { value: 'id', label: 'ID' },
    { value: 'emag_id', label: 'ID eMAG' },
    { value: 'name', label: 'Nume Produs' },
    { value: 'brand', label: 'Brand' },
    { value: 'part_number', label: 'Part Number' },
    { value: 'category_id', label: 'Categorie' },
    { value: 'price', label: 'Preț' },
    { value: 'sale_price', label: 'Preț Vânzare' },
    { value: 'min_sale_price', label: 'Preț Minim' },
    { value: 'max_sale_price', label: 'Preț Maxim' },
    { value: 'stock', label: 'Stoc' },
    { value: 'reserved_stock', label: 'Stoc Rezervat' },
    { value: 'available_stock', label: 'Stoc Disponibil' },
    { value: 'ean', label: 'Cod EAN' },
    { value: 'description', label: 'Descriere' },
    { value: 'warranty', label: 'Garanție' },
    { value: 'vat_id', label: 'TVA' },
    { value: 'handling_time', label: 'Timp Procesare' },
    { value: 'status', label: 'Status' },
    { value: 'account_type', label: 'Tip Cont' },
    { value: 'sync_status', label: 'Status Sincronizare' },
    { value: 'created_at', label: 'Data Creare' },
    { value: 'updated_at', label: 'Data Actualizare' },
  ];

  // Handle export
  const handleExport = async () => {
    try {
      setUploading(true);
      setProgress(0);

      const params: any = {
        format: exportFormat,
        fields: exportFields.join(','),
      };

      if (selectedProductIds.length > 0) {
        params.product_ids = selectedProductIds.join(',');
      }

      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return prev;
          }
          return prev + 10;
        });
      }, 200);

      const response = await api.get('/products-v1/export', {
        params,
        responseType: 'blob',
      });

      clearInterval(progressInterval);
      setProgress(100);

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      const extension = exportFormat === 'csv' ? 'csv' : exportFormat === 'pdf' ? 'pdf' : 'xlsx';
      link.setAttribute('download', `products_export_${Date.now()}.${extension}`);
      
      document.body.appendChild(link);
      link.click();
      link.remove();

      message.success('Export finalizat cu succes!');
      setTimeout(() => {
        onClose();
        setProgress(0);
      }, 1000);
    } catch (error: any) {
      console.error('Export error:', error);
      message.error(error.response?.data?.detail || 'Eroare la export');
    } finally {
      setUploading(false);
    }
  };

  // Handle import
  const handleImport = async () => {
    if (fileList.length === 0) {
      message.warning('Selectați un fișier pentru import');
      return;
    }

    try {
      setUploading(true);
      setProgress(0);

      const formData = new FormData();
      formData.append('file', fileList[0] as any);

      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return prev;
          }
          return prev + 10;
        });
      }, 300);

      const response = await api.post('/products-v1/import', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      clearInterval(progressInterval);
      setProgress(100);

      if (response.data) {
        setImportResult(response.data);
        message.success('Import finalizat cu succes!');
      }
    } catch (error: any) {
      console.error('Import error:', error);
      message.error(error.response?.data?.detail || 'Eroare la import');
    } finally {
      setUploading(false);
    }
  };

  // Handle file upload
  const handleUploadChange = (info: any) => {
    let newFileList = [...info.fileList];
    newFileList = newFileList.slice(-1); // Keep only last file
    setFileList(newFileList);
  };

  // Download template
  const handleDownloadTemplate = async () => {
    try {
      const response = await api.get('/products-v1/export-template', {
        params: { format: exportFormat },
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      const extension = exportFormat === 'csv' ? 'csv' : 'xlsx';
      link.setAttribute('download', `products_template.${extension}`);
      
      document.body.appendChild(link);
      link.click();
      link.remove();

      message.success('Template descărcat cu succes!');
    } catch (error) {
      console.error('Template download error:', error);
      message.error('Eroare la descărcarea template-ului');
    }
  };

  return (
    <Modal
      title={mode === 'export' ? 'Export Produse' : 'Import Produse'}
      open={visible}
      onCancel={onClose}
      width={600}
      footer={[
        <Button key="cancel" onClick={onClose}>
          Anulează
        </Button>,
        mode === 'export' ? (
          <Button
            key="export"
            type="primary"
            icon={<DownloadOutlined />}
            onClick={handleExport}
            loading={uploading}
          >
            Exportă
          </Button>
        ) : (
          <Button
            key="import"
            type="primary"
            icon={<UploadOutlined />}
            onClick={handleImport}
            loading={uploading}
            disabled={fileList.length === 0}
          >
            Importă
          </Button>
        ),
      ]}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {mode === 'export' ? (
          <>
            {/* Export Format */}
            <div>
              <Text strong>Format Export:</Text>
              <Radio.Group
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value)}
                style={{ marginTop: 8, display: 'block' }}
              >
                <Space direction="vertical">
                  <Radio value="excel">
                    <FileExcelOutlined style={{ color: '#217346' }} /> Excel (.xlsx)
                  </Radio>
                  <Radio value="csv">
                    <FileExcelOutlined style={{ color: '#52c41a' }} /> CSV (.csv)
                  </Radio>
                  <Radio value="pdf">
                    <FilePdfOutlined style={{ color: '#ff4d4f' }} /> PDF (.pdf)
                  </Radio>
                </Space>
              </Radio.Group>
            </div>

            <Divider />

            {/* Export Fields */}
            <div>
              <Text strong>Câmpuri de Exportat:</Text>
              <Checkbox.Group
                value={exportFields}
                onChange={(values) => setExportFields(values as string[])}
                style={{ marginTop: 8, display: 'block' }}
              >
                <Space direction="vertical">
                  {allFields.map((field) => (
                    <Checkbox key={field.value} value={field.value}>
                      {field.label}
                    </Checkbox>
                  ))}
                </Space>
              </Checkbox.Group>
            </div>

            {selectedProductIds.length > 0 && (
              <Alert
                message={`Se vor exporta ${selectedProductIds.length} produse selectate`}
                type="info"
                showIcon
              />
            )}
          </>
        ) : (
          <>
            {/* Import Instructions */}
            <Alert
              message="Instrucțiuni Import"
              description={
                <ul style={{ paddingLeft: 20, marginBottom: 0 }}>
                  <li>Descărcați template-ul pentru format corect</li>
                  <li>Completați datele în template</li>
                  <li>Încărcați fișierul completat (.xlsx sau .csv)</li>
                  <li>Verificați rezultatele importului</li>
                </ul>
              }
              type="info"
              showIcon
            />

            {/* Download Template */}
            <div>
              <Text strong>Format Template:</Text>
              <div style={{ marginTop: 8 }}>
                <Space>
                  <Select
                    value={exportFormat}
                    onChange={setExportFormat}
                    style={{ width: 150 }}
                  >
                    <Option value="excel">Excel (.xlsx)</Option>
                    <Option value="csv">CSV (.csv)</Option>
                  </Select>
                  <Button
                    icon={<DownloadOutlined />}
                    onClick={handleDownloadTemplate}
                  >
                    Descarcă Template
                  </Button>
                </Space>
              </div>
            </div>

            <Divider />

            {/* File Upload */}
            <div>
              <Text strong>Încarcă Fișier:</Text>
              <Upload
                fileList={fileList}
                onChange={handleUploadChange}
                beforeUpload={() => false}
                accept=".xlsx,.xls,.csv"
                maxCount={1}
                style={{ marginTop: 8 }}
              >
                <Button icon={<UploadOutlined />} block>
                  Selectează Fișier
                </Button>
              </Upload>
            </div>

            {/* Import Result */}
            {importResult && (
              <>
                <Divider />
                <Alert
                  message="Rezultat Import"
                  description={
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Text>
                        <CheckCircleOutlined style={{ color: '#52c41a' }} />{' '}
                        Produse importate: {importResult.imported || 0}
                      </Text>
                      {importResult.errors && importResult.errors.length > 0 && (
                        <Text type="danger">
                          Erori: {importResult.errors.length}
                        </Text>
                      )}
                    </Space>
                  }
                  type={importResult.errors?.length > 0 ? 'warning' : 'success'}
                  showIcon
                />
              </>
            )}
          </>
        )}

        {/* Progress */}
        {uploading && (
          <>
            <Divider />
            <div>
              <Text strong>Progres:</Text>
              <Progress percent={progress} status="active" />
            </div>
          </>
        )}
      </Space>
    </Modal>
  );
};

export default ExportImport;
