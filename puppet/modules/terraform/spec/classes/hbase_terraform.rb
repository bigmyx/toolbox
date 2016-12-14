require 'spec_helper'

describe 'hbase' do
  context 'minimal compile check' do
      it { should compile.with_all_deps }

      it { is_expected.to contain_class('Terraform') }
      it { is_expected.to contain_class('Terraform::Install') }
      it { is_expected.to contain_package('hbase').with_ensure('present') }
  end
end

