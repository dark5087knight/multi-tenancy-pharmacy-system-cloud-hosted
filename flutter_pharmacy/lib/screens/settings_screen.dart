import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../providers/workspace_provider.dart';
import '../widgets/page_header.dart';
import '../theme/theme.dart';
import '../i18n/translations.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _apiUrlController = TextEditingController();
  final _branchController = TextEditingController();
  final _addressController = TextEditingController();
  final _taxController = TextEditingController();
  final _marginController = TextEditingController();

  @override
  void initState() {
    super.initState();
    final workspace = Provider.of<WorkspaceProvider>(context, listen: false);
    _apiUrlController.text = workspace.backendUrl;
    _branchController.text = workspace.branchLabel;
    _addressController.text = workspace.branchAddress;
    _taxController.text = workspace.vatTax;
    _marginController.text = workspace.profitMargin;
    _autoBackup = workspace.autoBackup;
    _lowStockAlerts = workspace.lowStockAlerts;
    _prescChecks = workspace.prescChecks;
  }

  @override
  void dispose() {
    _apiUrlController.dispose();
    _branchController.dispose();
    _addressController.dispose();
    _taxController.dispose();
    _marginController.dispose();
    super.dispose();
  }
  
  bool _autoBackup = true;
  bool _lowStockAlerts = true;
  bool _prescChecks = true;

  @override
  Widget build(BuildContext context) {
    final appColors = Theme.of(context).extension<AppColors>()!;
    final workspace = Provider.of<WorkspaceProvider>(context);

    return Scaffold(
      backgroundColor: appColors.background,
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          PageHeader(
            icon: LucideIcons.settings,
            title: context.tr('settings.title'),
            subtitle: context.tr('settings.subtitle'),
          ),
          Expanded(
            child: ListView(
               padding: const EdgeInsets.all(20),
              children: [
                // API Connection
                Section(
                  title: 'API Connection Settings',
                  children: Column(
                    children: [
                      _buildField('Backend API URL', _apiUrlController),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // Branch Profile
                Section(
                  title: context.tr('settings.branch_profile'),
                  children: Column(
                    children: [
                      _buildField(context.tr('settings.branch_label_field'), _branchController),
                      _buildField(context.tr('settings.branch_address_field'), _addressController),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // Pricing Rules
                Section(
                  title: context.tr('settings.margin_rules'),
                  children: Row(
                    children: [
                      Expanded(child: _buildField(context.tr('settings.vat_tax'), _taxController, number: true)),
                      const SizedBox(width: 16),
                      Expanded(child: _buildField(context.tr('settings.profit_margin'), _marginController, number: true)),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // Language settings
                Section(
                  title: context.tr('settings.language_section'),
                  children: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(context.tr('settings.select_language'), style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w500)),
                        const SizedBox(height: 8),
                        DropdownButtonFormField<String>(
                          initialValue: workspace.locale,
                          style: TextStyle(color: appColors.foreground, fontSize: 13),
                          decoration: const InputDecoration(
                            isDense: true,
                            contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                          ),
                          items: const [
                            DropdownMenuItem(value: 'ar', child: Text('العربية (Arabic)')),
                            DropdownMenuItem(value: 'en', child: Text('English')),
                          ],
                          onChanged: (val) {
                            if (val != null) {
                              workspace.setLocale(val);
                            }
                          },
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 20),

                // System Actions
                Section(
                  title: context.tr('settings.operations_pipelines'),
                  children: Column(
                    children: [
                      SwitchListTile(
                        title: Text(context.tr('settings.cloud_backups'), style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold)),
                        subtitle: Text(context.tr('settings.cloud_backups_sub'), style: const TextStyle(fontSize: 11)),
                        value: _autoBackup,
                        onChanged: (val) => setState(() => _autoBackup = val),
                      ),
                      SwitchListTile(
                        title: Text(context.tr('settings.low_stock'), style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold)),
                        subtitle: Text(context.tr('settings.low_stock_sub'), style: const TextStyle(fontSize: 11)),
                        value: _lowStockAlerts,
                        onChanged: (val) => setState(() => _lowStockAlerts = val),
                      ),
                      SwitchListTile(
                        title: Text(context.tr('settings.licenses'), style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold)),
                        subtitle: Text(context.tr('settings.licenses_sub'), style: const TextStyle(fontSize: 11)),
                        value: _prescChecks,
                        onChanged: (val) => setState(() => _prescChecks = val),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: appColors.foreground,
                    foregroundColor: appColors.background,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                  ),
                  onPressed: () async {
                    final workspace = Provider.of<WorkspaceProvider>(context, listen: false);
                    
                    // 1. Validate and update API connection first
                    final urlSuccess = await workspace.updateBackendUrl(_apiUrlController.text);
                    if (!urlSuccess) return;

                    // If the backend changed, the user is logged out and this widget gets unmounted.
                    // Only proceed to save the rest if still mounted.
                    if (!context.mounted) return;

                    // 2. Save other settings
                    await workspace.updateSettings(
                      branchLabel: _branchController.text,
                      branchAddress: _addressController.text,
                      vatTax: _taxController.text,
                      profitMargin: _marginController.text,
                      autoBackup: _autoBackup,
                      lowStockAlerts: _lowStockAlerts,
                      prescChecks: _prescChecks,
                    );
                    
                    if (context.mounted) {
                      workspace.showNotification(
                        title: context.tr('settings.saved_toast'),
                        body: '',
                        category: 'system',
                      );
                    }
                  },
                  child: Text(context.tr('settings.save_btn'), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildField(String label, TextEditingController controller, {bool number = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w500)),
          const SizedBox(height: 4),
          TextFormField(
            controller: controller,
            keyboardType: number ? TextInputType.number : TextInputType.text,
            style: const TextStyle(fontSize: 12),
            decoration: const InputDecoration(
              isDense: true,
              contentPadding: EdgeInsets.all(10),
            ),
          ),
        ],
      ),
    );
  }
}
